package com.sjtu.runner.utils

import android.content.Context
import kotlin.math.*

object GpsUtil {
    const val EARTH_RADIUS = 6371000.0

    fun haversineDistance(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val a = sin(dLat / 2).pow(2) +
                cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) *
                sin(dLon / 2).pow(2)
        val c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return EARTH_RADIUS * c
    }

    fun readCoordinates(context: Context): List<Pair<Double, Double>> {
        val list = mutableListOf<Pair<Double, Double>>()
        context.resources.openRawResource(
            context.resources.getIdentifier("route_coordinates", "raw", context.packageName)
        ).bufferedReader().use { reader ->
            reader.lineSequence().forEach { line ->
                val parts = line.trim().split(",")
                if (parts.size == 2) {
                    list.add(parts[0].toDouble() to parts[1].toDouble())
                }
            }
        }
        return list
    }
}