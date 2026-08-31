package ir.rahyar.app.data.trip

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

data class TripStoryRecord(
    val tripId: String,
    val startedAtMillis: Long,
    val endedAtMillis: Long,
    val actualDistanceKm: Double,
    val actualDurationMinutes: Int,
    val averageSpeedKmh: Double,
    val maxSpeedKmh: Double,
    val rerouteCount: Int,
    val stopCount: Int,
    val mediaCount: Int,
    val weatherEventCount: Int,
    val trafficEventCount: Int,
    val navigationRating: Int?
)

object TripStoryStore {
    private const val PREFS = "rahyar_trip_story"
    private const val KEY_ITEMS = "items"
    private const val MAX_ITEMS = 50

    fun save(
        context: Context,
        record: TripStoryRecord
    ) {
        val prefs = context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)

        val current = runCatching {
            JSONArray(prefs.getString(KEY_ITEMS, "[]") ?: "[]")
        }.getOrElse {
            JSONArray()
        }

        val updated = JSONArray()
        updated.put(record.toJson())

        for (index in 0 until minOf(current.length(), MAX_ITEMS - 1)) {
            current.optJSONObject(index)?.let(updated::put)
        }

        prefs.edit()
            .putString(KEY_ITEMS, updated.toString())
            .apply()
    }

    fun load(context: Context): List<TripStoryRecord> {
        val prefs = context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val raw = prefs.getString(KEY_ITEMS, "[]") ?: "[]"
        val array = runCatching { JSONArray(raw) }.getOrElse { JSONArray() }

        return buildList {
            for (index in 0 until array.length()) {
                array.optJSONObject(index)?.toRecord()?.let(::add)
            }
        }
    }

    private fun JSONObject.toRecord(): TripStoryRecord? {
        val tripId = optString("tripId").trim()
        if (tripId.isBlank()) return null
        return TripStoryRecord(
            tripId = tripId,
            startedAtMillis = optLong("startedAtMillis", 0L),
            endedAtMillis = optLong("endedAtMillis", 0L),
            actualDistanceKm = optDouble("actualDistanceKm", 0.0),
            actualDurationMinutes = optInt("actualDurationMinutes", 0),
            averageSpeedKmh = optDouble("averageSpeedKmh", 0.0),
            maxSpeedKmh = optDouble("maxSpeedKmh", 0.0),
            rerouteCount = optInt("rerouteCount", 0),
            stopCount = optInt("stopCount", 0),
            mediaCount = optInt("mediaCount", 0),
            weatherEventCount = optInt("weatherEventCount", 0),
            trafficEventCount = optInt("trafficEventCount", 0),
            navigationRating =
                if (has("navigationRating")) optInt("navigationRating")
                else null
        )
    }

    private fun TripStoryRecord.toJson(): JSONObject =
        JSONObject().apply {
            put("tripId", tripId)
            put("startedAtMillis", startedAtMillis)
            put("endedAtMillis", endedAtMillis)
            put("actualDistanceKm", actualDistanceKm)
            put("actualDurationMinutes", actualDurationMinutes)
            put("averageSpeedKmh", averageSpeedKmh)
            put("maxSpeedKmh", maxSpeedKmh)
            put("rerouteCount", rerouteCount)
            put("stopCount", stopCount)
            put("mediaCount", mediaCount)
            put("weatherEventCount", weatherEventCount)
            put("trafficEventCount", trafficEventCount)
            if (navigationRating != null) {
                put("navigationRating", navigationRating)
            }
        }
}
