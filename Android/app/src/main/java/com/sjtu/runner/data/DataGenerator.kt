package com.sjtu.runner.data

import com.sjtu.runner.utils.GpsUtil
import kotlin.math.*
import java.util.UUID

object DataGenerator {

    private const val OFFSET_LON = -0.00651271494735 + 0.000094
    private const val OFFSET_LAT = -0.00560888976477 - 0.000700

    suspend fun generate(
        coordinates: List<Pair<Double, Double>>,
        userId: String,
        targetDistanceM: Int,
        startTimeMs: Long,
        intervalSeconds: Int = 3,
        log: (String) -> Unit
    ): Pair<List<Map<String, Any>>, Double> {

        val corrected = coordinates.map { (lon, lat) ->
            (lon + OFFSET_LON) to (lat + OFFSET_LAT)
        }
        log("坐标已校正，共 ${corrected.size} 个点")

        val singleLoopDistance = if (corrected.size > 1) {
            corrected.zipWithNext { a, b ->
                GpsUtil.haversineDistance(a.second, a.first, b.second, b.first)
            }.sum()
        } else 0.0
        log("单圈距离: ${String.format("%.2f", singleLoopDistance)}m，目标: ${targetDistanceM}m")

        val paceMinPerKm = 4.0
        val totalDurationSec = (paceMinPerKm * 60 * targetDistanceM / 1000.0).roundToInt()
        val targetSpeedMps = targetDistanceM.toDouble() / totalDurationSec
        log("目标速度: ${String.format("%.2f", targetSpeedMps)} m/s")

        val adjustedCoords = adjustPath(
            corrected,
            targetDistanceM.toDouble(),
            targetSpeedMps,
            intervalSeconds,
            log
        )
        log("调整后路径点数: ${adjustedCoords.size}")

        val pointsWithTime = generateTrackPoints(
            adjustedCoords,
            startTimeMs,
            targetSpeedMps,
            intervalSeconds
        )
        log("生成轨迹点 ${pointsWithTime.size} 个")

        val tracks = splitIntoSegments(pointsWithTime)

        var actualDistance = 0.0
        if (pointsWithTime.size >= 2) {
            for (i in 0 until pointsWithTime.size - 1) {
                val p1 = pointsWithTime[i]["latLng"] as Map<*, *>
                val p2 = pointsWithTime[i + 1]["latLng"] as Map<*, *>
                actualDistance += GpsUtil.haversineDistance(
                    p1["latitude"] as Double,
                    p1["longitude"] as Double,
                    p2["latitude"] as Double,
                    p2["longitude"] as Double
                )
            }
        }

        val actualDurationSec = if (pointsWithTime.size >= 2) {
            ((pointsWithTime.last()["locatetime"] as Long) - (pointsWithTime.first()["locatetime"] as Long)) / 1000.0
        } else 0.0
        val avgPaceMinPerKm = if (actualDistance > 0) actualDurationSec / (actualDistance / 1000.0) / 60.0 else 0.0
        val spAvg = min(max(avgPaceMinPerKm.roundToInt(), 3), 9)

        val payload = listOf(
            mapOf(
                "fravg" to 0,
                "id" to 9,
                "sid" to UUID.randomUUID().toString(),
                "signpoints" to emptyList<Any>(),
                "spavg" to spAvg,
                "state" to "0",
                "tracks" to tracks,
                "userId" to userId
            )
        )

        return payload to actualDistance
    }

    private fun adjustPath(
        original: List<Pair<Double, Double>>,
        targetDistance: Double,
        speedMps: Double,
        intervalSec: Int,
        log: (String) -> Unit
    ): List<Pair<Double, Double>> {
        val stepDist = speedMps * intervalSec
        val detailed = mutableListOf(original.first())
        for (i in 0 until original.size - 1) {
            val (lon1, lat1) = original[i]
            val (lon2, lat2) = original[i + 1]
            val dist = GpsUtil.haversineDistance(lat1, lon1, lat2, lon2)
            val steps = max(1, (dist / stepDist).roundToInt())
            for (j in 1..steps) {
                val f = j.toDouble() / (steps + 1)
                val lon = lon1 + f * (lon2 - lon1)
                val lat = lat1 + f * (lat2 - lat1)
                detailed.add(lon to lat)
            }
            detailed.add(original[i + 1])
        }

        val singleLoop = detailed.zipWithNext { a, b ->
            GpsUtil.haversineDistance(a.second, a.first, b.second, b.first)
        }.sum()

        if (singleLoop >= targetDistance) {
            var acc = 0.0
            val truncated = mutableListOf(detailed.first())
            for (i in 0 until detailed.size - 1) {
                val seg = GpsUtil.haversineDistance(
                    detailed[i].second, detailed[i].first,
                    detailed[i + 1].second, detailed[i + 1].first
                )
                if (acc + seg >= targetDistance) {
                    val rem = targetDistance - acc
                    val f = if (seg > 0) rem / seg else 0.0
                    val lastLon = detailed[i].first + f * (detailed[i + 1].first - detailed[i].first)
                    val lastLat = detailed[i].second + f * (detailed[i + 1].second - detailed[i].second)
                    truncated.add(lastLon to lastLat)
                    break
                }
                truncated.add(detailed[i + 1])
                acc += seg
            }
            return truncated
        }

        val fullLoops = (targetDistance / singleLoop).toInt()
        val remainder = targetDistance - fullLoops * singleLoop

        val result = mutableListOf<Pair<Double, Double>>()
        repeat(fullLoops) { result.addAll(detailed) }
        var acc = 0.0
        for (i in 0 until detailed.size - 1) {
            val seg = GpsUtil.haversineDistance(
                detailed[i].second, detailed[i].first,
                detailed[i + 1].second, detailed[i + 1].first
            )
            if (acc + seg >= remainder) {
                val rem = remainder - acc
                val f = if (seg > 0) rem / seg else 0.0
                val lastLon = detailed[i].first + f * (detailed[i + 1].first - detailed[i].first)
                val lastLat = detailed[i].second + f * (detailed[i + 1].second - detailed[i].second)
                result.add(lastLon to lastLat)
                break
            }
            result.add(detailed[i + 1])
            acc += seg
        }
        log("最终路径: ${fullLoops}圈 + 余量 ${String.format("%.2f", remainder)}m")
        return result
    }

    private fun generateTrackPoints(
        coords: List<Pair<Double, Double>>,
        startTimeMs: Long,
        speedMps: Double,
        intervalSec: Int
    ): List<Map<String, Any>> {
        val points = mutableListOf<Map<String, Any>>()
        var cumDist = 0.0
        coords.forEachIndexed { i, (lon, lat) ->
            if (i > 0) {
                val prev = coords[i - 1]
                cumDist += GpsUtil.haversineDistance(prev.second, prev.first, lat, lon)
            }
            val elapsed = cumDist / speedMps
            val time = startTimeMs + (elapsed * 1000).toLong()
            points.add(
                mapOf(
                    "latLng" to mapOf("latitude" to lat, "longitude" to lon),
                    "location" to "${String.format("%.14f", lon)},${String.format("%.14f", lat)}",
                    "step" to 0,
                    "locatetime" to time
                )
            )
        }
        return points
    }

    private fun splitIntoSegments(allPoints: List<Map<String, Any>>): List<Map<String, Any>> {
        val tracks = mutableListOf<Map<String, Any>>()
        var idx = 0
        while (idx < allPoints.size) {
            val take = min(
                max(5, (allPoints.size - idx) / (2 + (Math.random() * 3).toInt())),
                allPoints.size - idx
            )
            val segmentPoints = allPoints.subList(idx, idx + take)
            idx += take

            val status = when {
                Math.random() < 0.8 -> "normal"
                Math.random() < 0.9 -> "invalid"
                else -> "stop"
            }
            val tstate = if (status == "invalid") "2" else "0"
            val dist = if (segmentPoints.size >= 2) {
                segmentPoints.zipWithNext { a, b ->
                    val al = a["latLng"] as Map<*, *>
                    val bl = b["latLng"] as Map<*, *>
                    GpsUtil.haversineDistance(
                        al["latitude"] as Double, al["longitude"] as Double,
                        bl["latitude"] as Double, bl["longitude"] as Double
                    )
                }.sum()
            } else 0.0

            val startTime = segmentPoints.first()["locatetime"] as Long
            val endTime = segmentPoints.last()["locatetime"] as Long
            tracks.add(
                mapOf(
                    "counts" to segmentPoints.size,
                    "distance" to dist,
                    "duration" to ((endTime - startTime) / 1000.0).roundToInt(),
                    "points" to segmentPoints,
                    "status" to status,
                    "trid" to UUID.randomUUID().toString(),
                    "tstate" to tstate,
                    "stime" to (startTime / 1000).toInt(),
                    "etime" to (endTime / 1000).toInt()
                )
            )
        }
        return tracks
    }
}