//
//  DataGenerator.swift
//  SJTURunningMan
//
//  Created by Jie Tang on 2026/5/4.
//


import Foundation

struct DataGenerator {

    static let offsetLon = -0.00651271494735 + 0.000094
    static let offsetLat = -0.00560888976477 - 0.000700

    struct TrackPoint {
        var latLng: [String: Double]       // "latitude", "longitude"
        var location: String               // "lon,lat"
        var step: Int                      // 0
        var locatetime: Int64              // ms
    }

    static func generate(coordinates: [Coord],
                          userId: String,
                          targetDistanceM: Int,
                          startTimeMs: Int64,
                          intervalSeconds: Int = 3,
                          log: (String) -> Void) async -> (payload: [[String: Any]], actualDistance: Double) {
        let corrected = coordinates.map { Coord(lon: $0.lon + offsetLon,
                                                  lat: $0.lat + offsetLat) }
        log("坐标已校正，共 \(corrected.count) 个点")

        let singleLoopDistance = stride(from: 0, to: corrected.count - 1, by: 1)
            .map { GpsUtil.haversineDistance(lat1: corrected[$0].lat,
                                              lon1: corrected[$0].lon,
                                              lat2: corrected[$0+1].lat,
                                              lon2: corrected[$0+1].lon) }
            .reduce(0, +)
        log("单圈距离: \(String(format: "%.2f", singleLoopDistance))m，目标: \(targetDistanceM)m")

        // 配速随机化：在4-6分钟/公里范围内随机生成（4-6分配）
        let randomPaceMinPerKm = Double.random(in: 4.0...6.0)
        let totalDurationSec = Int((randomPaceMinPerKm * 60.0 * Double(targetDistanceM) / 1000.0).rounded())
        let targetSpeedMps = Double(targetDistanceM) / Double(totalDurationSec)
        log("使用随机配速: \(String(format: "%.1f", randomPaceMinPerKm)) 分钟/公里 (\(Int(randomPaceMinPerKm * 60)) 秒/公里)")
        log("目标速度: \(String(format: "%.2f", targetSpeedMps)) m/s")

        let adjustedCoords = adjustPath(original: corrected,
                                         targetDistance: Double(targetDistanceM),
                                         speedMps: targetSpeedMps,
                                         intervalSec: intervalSeconds,
                                         log: log)
        log("调整后路径点数: \(adjustedCoords.count)")

        let pointsWithTime = generateTrackPoints(coords: adjustedCoords,
                                                  startTimeMs: startTimeMs,
                                                  speedMps: targetSpeedMps,
                                                  intervalSec: intervalSeconds)
        log("生成轨迹点 \(pointsWithTime.count) 个")

        let tracks = splitIntoSegments(allPoints: pointsWithTime)

        var actualDistance = 0.0
        if pointsWithTime.count >= 2 {
            for i in 0..<(pointsWithTime.count - 1) {
                let p1 = pointsWithTime[i].latLng
                let p2 = pointsWithTime[i+1].latLng
                actualDistance += GpsUtil.haversineDistance(lat1: p1["latitude"]!,
                                                             lon1: p1["longitude"]!,
                                                             lat2: p2["latitude"]!,
                                                             lon2: p2["longitude"]!)
            }
        }

        let actualDurationSec = pointsWithTime.count >= 2 ?
            Double(pointsWithTime.last!.locatetime - pointsWithTime.first!.locatetime) / 1000.0 : 0.0
        let avgPaceMinPerKm = actualDistance > 0 ?
            actualDurationSec / (actualDistance / 1000.0) / 60.0 : 0.0
        let spAvg = min(max(Int(avgPaceMinPerKm.rounded()), 3), 9)

        let payload: [[String: Any]] = [[
            "fravg": 0,
            "id": 9,
            "sid": UUID().uuidString,
            "signpoints": [],
            "spavg": spAvg,
            "state": "0",
            "tracks": tracks,
            "userId": userId
        ]]

        return (payload, actualDistance)
    }

    private static func adjustPath(original: [Coord],
                                    targetDistance: Double,
                                    speedMps: Double,
                                    intervalSec: Int,
                                    log: (String) -> Void) -> [Coord] {
        let stepDist = speedMps * Double(intervalSec)
        var detailed: [Coord] = [original.first!]
        for i in 0..<(original.count - 1) {
            let (a, b) = (original[i], original[i+1])
            let dist = GpsUtil.haversineDistance(lat1: a.lat, lon1: a.lon,
                                                  lat2: b.lat, lon2: b.lon)
            let steps = max(1, Int((dist / stepDist).rounded()))
            for j in 1...steps {
                let f = Double(j) / Double(steps + 1)
                let lon = a.lon + f * (b.lon - a.lon)
                let lat = a.lat + f * (b.lat - a.lat)
                detailed.append(Coord(lon: lon, lat: lat))
            }
            detailed.append(b)
        }

        let singleLoop = stride(from: 0, to: detailed.count - 1, by: 1)
            .map { GpsUtil.haversineDistance(lat1: detailed[$0].lat,
                                              lon1: detailed[$0].lon,
                                              lat2: detailed[$0+1].lat,
                                              lon2: detailed[$0+1].lon) }
            .reduce(0, +)

        if singleLoop >= targetDistance {
            var acc = 0.0
            var truncated = [detailed.first!]
            for i in 0..<(detailed.count - 1) {
                let seg = GpsUtil.haversineDistance(lat1: detailed[i].lat,
                                                     lon1: detailed[i].lon,
                                                     lat2: detailed[i+1].lat,
                                                     lon2: detailed[i+1].lon)
                if acc + seg >= targetDistance {
                    let rem = targetDistance - acc
                    let f = seg > 0 ? rem / seg : 0.0
                    let lastLon = detailed[i].lon + f * (detailed[i+1].lon - detailed[i].lon)
                    let lastLat = detailed[i].lat + f * (detailed[i+1].lat - detailed[i].lat)
                    truncated.append(Coord(lon: lastLon, lat: lastLat))
                    break
                }
                truncated.append(detailed[i+1])
                acc += seg
            }
            return truncated
        }

        let fullLoops = Int(targetDistance / singleLoop)
        let remainder = targetDistance - Double(fullLoops) * singleLoop
        var result: [Coord] = []
        for _ in 0..<fullLoops {
            result.append(contentsOf: detailed)
        }
        var acc = 0.0
        for i in 0..<(detailed.count - 1) {
            let seg = GpsUtil.haversineDistance(lat1: detailed[i].lat,
                                                 lon1: detailed[i].lon,
                                                 lat2: detailed[i+1].lat,
                                                 lon2: detailed[i+1].lon)
            if acc + seg >= remainder {
                let rem = remainder - acc
                let f = seg > 0 ? rem / seg : 0.0
                let lastLon = detailed[i].lon + f * (detailed[i+1].lon - detailed[i].lon)
                let lastLat = detailed[i].lat + f * (detailed[i+1].lat - detailed[i].lat)
                result.append(Coord(lon: lastLon, lat: lastLat))
                break
            }
            result.append(detailed[i+1])
            acc += seg
        }
        log("最终路径: \(fullLoops)圈 + 余量 \(String(format: "%.2f", remainder))m")
        return result
    }

    private static func generateTrackPoints(coords: [Coord],
                                             startTimeMs: Int64,
                                             speedMps: Double,
                                             intervalSec: Int) -> [TrackPoint] {
        var points: [TrackPoint] = []
        var cumDist = 0.0
        for (i, coord) in coords.enumerated() {
            if i > 0 {
                let prev = coords[i-1]
                cumDist += GpsUtil.haversineDistance(lat1: prev.lat, lon1: prev.lon,
                                                      lat2: coord.lat, lon2: coord.lon)
            }
            let elapsed = cumDist / speedMps
            let time = startTimeMs + Int64(elapsed * 1000)
            let pt = TrackPoint(
                latLng: ["latitude": coord.lat, "longitude": coord.lon],
                location: "\(String(format: "%.14f", coord.lon)),\(String(format: "%.14f", coord.lat))",
                step: 0,
                locatetime: time
            )
            points.append(pt)
        }
        return points
    }

    private static func splitIntoSegments(allPoints: [TrackPoint]) -> [[String: Any]] {
        var tracks: [[String: Any]] = []
        var idx = 0
        while idx < allPoints.count {
            let limit = min(allPoints.count - idx,
                            max(5, (allPoints.count - idx) / (2 + Int.random(in: 0...3))))
            let segment = Array(allPoints[idx..<idx+limit])
            idx += limit

            let status = Double.random(in: 0..<1) < 0.8 ? "normal" :
                         Double.random(in: 0..<1) < 0.9 ? "invalid" : "stop"
            let tstate = status == "invalid" ? "2" : "0"

            let dist = segment.count >= 2 ? stride(from: 0, to: segment.count-1, by: 1)
                .map { GpsUtil.haversineDistance(lat1: segment[$0].latLng["latitude"]!,
                                                 lon1: segment[$0].latLng["longitude"]!,
                                                 lat2: segment[$0+1].latLng["latitude"]!,
                                                 lon2: segment[$0+1].latLng["longitude"]!) }
                .reduce(0, +) : 0.0

            let startTime = segment.first!.locatetime
            let endTime = segment.last!.locatetime

            let segmentDict: [String: Any] = [
                "counts": segment.count,
                "distance": dist,
                "duration": Int((Double(endTime - startTime) / 1000.0).rounded()),
                "points": segment.map { pt -> [String: Any] in
                    return [
                        "latLng": pt.latLng,
                        "location": pt.location,
                        "step": pt.step,
                        "locatetime": pt.locatetime
                    ]
                },
                "status": status,
                "trid": UUID().uuidString,
                "tstate": tstate,
                "stime": Int(startTime / 1000),
                "etime": Int(endTime / 1000)
            ]
            tracks.append(segmentDict)
        }
        return tracks
    }
}