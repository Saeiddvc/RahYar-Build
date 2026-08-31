package ir.rahyar.app.data.home

import android.content.Context
import ir.rahyar.app.domain.models.LatLng
import org.json.JSONArray
import org.json.JSONObject

data class StoredPersonalPlace(
    val id: String,
    val label: String,
    val location: LatLng
)

object PersonalPlacesStore {
    private const val PREFS = "rahyar_personal_places"
    private const val KEY_HOME = "home"
    private const val KEY_WORK = "work"
    private const val KEY_SAVED = "saved"
    private const val MAX_SAVED = 12

    fun home(context: Context): StoredPersonalPlace? =
        readSingle(context, KEY_HOME)

    fun work(context: Context): StoredPersonalPlace? =
        readSingle(context, KEY_WORK)

    fun saveHome(context: Context, location: LatLng) {
        saveSingle(
            context,
            KEY_HOME,
            StoredPersonalPlace("home", "خانه", location)
        )
    }

    fun saveWork(context: Context, location: LatLng) {
        saveSingle(
            context,
            KEY_WORK,
            StoredPersonalPlace("work", "محل کار", location)
        )
    }

    fun savedPlaces(context: Context): List<StoredPersonalPlace> {
        val prefs = context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val raw = prefs.getString(KEY_SAVED, "[]") ?: "[]"
        val array = runCatching { JSONArray(raw) }.getOrElse { JSONArray() }

        return buildList {
            for (index in 0 until array.length()) {
                array.optJSONObject(index)?.toPlace()?.let(::add)
            }
        }
    }

    fun addSaved(
        context: Context,
        label: String,
        location: LatLng
    ) {
        val existing = savedPlaces(context).toMutableList()
        val id = "saved-" + System.currentTimeMillis()
        existing.removeAll {
            distanceKey(it.location) == distanceKey(location)
        }
        existing.add(
            0,
            StoredPersonalPlace(
                id = id,
                label = label.ifBlank { "مکان ذخیره‌شده" },
                location = location
            )
        )
        writeSaved(context, existing.take(MAX_SAVED))
    }

    fun removeSaved(context: Context, id: String) {
        writeSaved(
            context,
            savedPlaces(context).filterNot { it.id == id }
        )
    }

    private fun saveSingle(
        context: Context,
        key: String,
        place: StoredPersonalPlace
    ) {
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(key, place.toJson().toString())
            .apply()
    }

    private fun readSingle(
        context: Context,
        key: String
    ): StoredPersonalPlace? {
        val raw = context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(key, null)
            ?: return null
        return runCatching { JSONObject(raw).toPlace() }.getOrNull()
    }

    private fun writeSaved(
        context: Context,
        values: List<StoredPersonalPlace>
    ) {
        val array = JSONArray()
        values.forEach { array.put(it.toJson()) }
        context.applicationContext
            .getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_SAVED, array.toString())
            .apply()
    }

    private fun StoredPersonalPlace.toJson(): JSONObject =
        JSONObject().apply {
            put("id", id)
            put("label", label)
            put("lat", location.latitude)
            put("lon", location.longitude)
        }

    private fun JSONObject.toPlace(): StoredPersonalPlace? {
        val id = optString("id").trim()
        val label = optString("label").trim()
        if (id.isBlank() || label.isBlank() || !has("lat") || !has("lon")) {
            return null
        }
        val lat = optDouble("lat", Double.NaN)
        val lon = optDouble("lon", Double.NaN)
        if (!lat.isFinite() || !lon.isFinite()) return null
        return StoredPersonalPlace(
            id = id,
            label = label,
            location = LatLng(lat, lon)
        )
    }

    private fun distanceKey(location: LatLng): String =
        "%.5f:%.5f".format(
            java.util.Locale.US,
            location.latitude,
            location.longitude
        )
}
