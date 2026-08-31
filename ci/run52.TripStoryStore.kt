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
