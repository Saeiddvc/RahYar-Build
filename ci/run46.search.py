from pathlib import Path

root = Path(".")

ranking = root / "app/src/main/java/ir/rahyar/app/core/search/SearchRanking.kt"
ranking.parent.mkdir(parents=True, exist_ok=True)
ranking.write_text("""package ir.rahyar.app.core.search

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.SearchResult
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.ln
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

fun normalizePersianSearch(value: String): String {
    val digitMap = mapOf(
        '۰' to '0', '۱' to '1', '۲' to '2', '۳' to '3', '۴' to '4',
        '۵' to '5', '۶' to '6', '۷' to '7', '۸' to '8', '۹' to '9',
        '٠' to '0', '١' to '1', '٢' to '2', '٣' to '3', '٤' to '4',
        '٥' to '5', '٦' to '6', '٧' to '7', '٨' to '8', '٩' to '9'
    )
    val cleaned = value
        .replace('ي', 'ی')
        .replace('ى', 'ی')
        .replace('ك', 'ک')
        .replace('ؤ', 'و')
        .replace('ۀ', 'ه')
        .replace('ة', 'ه')
        .replace('\u200c', ' ')
        .map { digitMap[it] ?: it }
        .joinToString("")
        .replace(Regex("[\\u064B-\\u065F\\u0670]"), "")
        .replace(Regex("[^\\p{L}\\p{N}\\s]"), " ")
        .replace(Regex("\\s+"), " ")
        .trim()
        .lowercase()
    return cleaned
}

fun persianSemanticScore(query: String, result: SearchResult): Double {
    val q = normalizePersianSearch(query)
    if (q.isBlank()) return 0.0
    val title = normalizePersianSearch(result.title)
    val subtitle = normalizePersianSearch(result.subtitle.orEmpty())

    if (title == q) return 1.0
    if (title.startsWith(q) || q.startsWith(title)) return 0.96
    if (title.contains(q) || q.contains(title)) return 0.92

    val qTokens = q.split(' ').filter { it.isNotBlank() }
    val titleTokens = title.split(' ').filter { it.isNotBlank() }
    val subtitleTokens = subtitle.split(' ').filter { it.isNotBlank() }

    val titleTokenScore = tokenCoverage(qTokens, titleTokens)
    val subtitleTokenScore = tokenCoverage(qTokens, subtitleTokens) * 0.82
    val editScore = normalizedSimilarity(q, title) * 0.88
    return maxOf(titleTokenScore, subtitleTokenScore, editScore)
}

fun rankSearchResults(
    query: String,
    results: List<SearchResult>,
    bias: LatLng?,
    limit: Int = 8
): List<SearchResult> {
    data class Scored(
        val result: SearchResult,
        val semantic: Double,
        val distanceMeters: Double?
    )

    return results
        .distinctBy {
            val lat = (it.location.latitude * 10_000).roundToInt()
            val lon = (it.location.longitude * 10_000).roundToInt()
            "\${normalizePersianSearch(it.title)}|\$lat|\$lon"
        }
        .map { result ->
            Scored(
                result = result,
                semantic = persianSemanticScore(query, result),
                distanceMeters = bias?.let { geoDistanceMeters(it, result.location) }
            )
        }
        .filter { it.semantic >= 0.38 }
        .sortedWith(
            compareByDescending<Scored> { (it.semantic * 20.0).roundToInt() }
                .thenBy { it.distanceMeters ?: Double.MAX_VALUE }
                .thenByDescending { it.semantic }
                .thenBy { it.result.title.length }
        )
        .take(limit)
        .map { it.result }
}

private fun tokenCoverage(queryTokens: List<String>, candidateTokens: List<String>): Double {
    if (queryTokens.isEmpty() || candidateTokens.isEmpty()) return 0.0
    val matched = queryTokens.count { q ->
        candidateTokens.any { c ->
            c == q || c.startsWith(q) || q.startsWith(c) || normalizedSimilarity(q, c) >= 0.72
        }
    }
    return matched.toDouble() / queryTokens.size.toDouble()
}

private fun normalizedSimilarity(a: String, b: String): Double {
    if (a.isBlank() || b.isBlank()) return 0.0
    val distance = levenshtein(a, b)
    return 1.0 - distance.toDouble() / maxOf(a.length, b.length).toDouble()
}

private fun levenshtein(a: String, b: String): Int {
    if (a == b) return 0
    if (a.isEmpty()) return b.length
    if (b.isEmpty()) return a.length
    var previous = IntArray(b.length + 1) { it }
    var current = IntArray(b.length + 1)
    for (i in a.indices) {
        current[0] = i + 1
        for (j in b.indices) {
            val cost = if (a[i] == b[j]) 0 else 1
            current[j + 1] = minOf(
                current[j] + 1,
                previous[j + 1] + 1,
                previous[j] + cost
            )
        }
        val tmp = previous
        previous = current
        current = tmp
    }
    return previous[b.length]
}

private fun geoDistanceMeters(a: LatLng, b: LatLng): Double {
    val radius = 6_371_000.0
    val dLat = Math.toRadians(b.latitude - a.latitude)
    val dLon = Math.toRadians(b.longitude - a.longitude)
    val lat1 = Math.toRadians(a.latitude)
    val lat2 = Math.toRadians(b.latitude)
    val h = sin(dLat / 2) * sin(dLat / 2) +
        cos(lat1) * cos(lat2) * sin(dLon / 2) * sin(dLon / 2)
    return radius * 2 * atan2(sqrt(h), sqrt(1 - h))
}
""")

test = root / "app/src/test/java/ir/rahyar/app/core/search/SearchRankingTest.kt"
test.parent.mkdir(parents=True, exist_ok=True)
test.write_text("""package ir.rahyar.app.core.search

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.SearchResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class SearchRankingTest {
    @Test fun arabicAndPersianCharactersNormalizeToSameText() {
        assertEquals(
            normalizePersianSearch("بانک شهر ساختمان ۲"),
            normalizePersianSearch("بانك شهر ساختمان 2")
        )
    }

    @Test fun minorPersianTypoStillMatches() {
        val result = SearchResult("1", "ساختمان شماره ۲ بانک شهر", "تهران", LatLng(35.7, 51.4))
        assertTrue(persianSemanticScore("ساختمون شماره 2 بانک شهر", result) >= 0.38)
    }

    @Test fun irrelevantRandomResultIsRejected() {
        val random = SearchResult("x", "معدن مس سرچشمه", "کرمان", LatLng(30.0, 56.0))
        assertTrue(rankSearchResults("ساختمان بانک شهر", listOf(random), LatLng(35.8, 50.9)).isEmpty())
    }

    @Test fun closerResultWinsWhenSemanticBucketIsEqual() {
        val near = SearchResult("near", "بانک شهر", "کرج", LatLng(35.82, 50.98))
        val far = SearchResult("far", "بانک شهر", "کرمان", LatLng(30.28, 57.08))
        val ranked = rankSearchResults("بانک شهر", listOf(far, near), LatLng(35.83, 50.99))
        assertEquals("near", ranked.first().id)
    }

    @Test fun exactRelevantResultBeatsNearbyUnrelatedResult() {
        val exact = SearchResult("exact", "ساختمان شماره ۲ بانک شهر", "تهران", LatLng(35.73, 51.42))
        val unrelated = SearchResult("near", "بانک دیگری", "کرج", LatLng(35.83, 50.99))
        val ranked = rankSearchResults("ساختمان شماره 2 بانک شهر", listOf(unrelated, exact), LatLng(35.83, 50.99))
        assertEquals("exact", ranked.first().id)
    }
}
""")

repo = root / "app/src/main/java/ir/rahyar/app/data/repository/DestinationSearchRepositoryImpl.kt"
text = repo.read_text()

imports = [
    ("import android.content.Context\\n", "import android.Manifest\\nimport android.content.Context\\nimport android.content.pm.PackageManager\\nimport android.location.LocationManager\\n"),
    ("import ir.rahyar.app.domain.models.LatLng\\n", "import ir.rahyar.app.domain.models.LatLng\\nimport ir.rahyar.app.core.search.rankSearchResults\\n"),
    ("import org.json.JSONArray\\n", "import org.json.JSONArray\\nimport org.json.JSONObject\\n"),
]
for old, new in imports:
    if new.splitlines()[0] not in text:
        if old not in text:
            raise SystemExit(f"Run46 import anchor missing: {old!r}")
        text = text.replace(old, new, 1)

class_anchor = """class DestinationSearchRepositoryImpl(
    context: Context
) : DestinationSearchRepository {

    private val prefs = context.getSharedPreferences("rahyar_recent_destinations", Context.MODE_PRIVATE)
"""
class_replacement = """class DestinationSearchRepositoryImpl(
    context: Context
) : DestinationSearchRepository {

    private val appContext = context.applicationContext
    private val prefs = context.getSharedPreferences("rahyar_recent_destinations", Context.MODE_PRIVATE)
"""
if class_anchor not in text:
    raise SystemExit("Run46 repository class anchor not found")
text = text.replace(class_anchor, class_replacement, 1)

start = text.index("    override suspend fun search(query: String): List<SearchResult> = withContext(Dispatchers.IO) {")
end = text.index("    override suspend fun searchAlongRoute(", start)

search_impl = """    override suspend fun search(query: String): List<SearchResult> = withContext(Dispatchers.IO) {
        val normalizedQuery = query.trim()
        if (normalizedQuery.length < 2) return@withContext emptyList()

        val bias = lastKnownBias()
        val photonAttempt = runCatching { fetchPhoton(normalizedQuery, bias) }
        val photon = photonAttempt.getOrDefault(emptyList())

        val combined = photon.toMutableList()
        if (combined.size < 6) {
            runCatching { fetchNominatim(normalizedQuery, bias) }
                .getOrDefault(emptyList())
                .let(combined::addAll)
        }

        if (combined.isEmpty() && photonAttempt.isFailure) {
            error("سرویس جستجوی مقصد در دسترس نیست")
        }

        rankSearchResults(
            query = normalizedQuery,
            results = combined,
            bias = bias,
            limit = 8
        )
    }

    private fun fetchPhoton(query: String, bias: LatLng?): List<SearchResult> {
        val encoded = URLEncoder.encode(query, Charsets.UTF_8.name())
        val biasPart = bias?.let { "&lat=\${it.latitude}&lon=\${it.longitude}" }.orEmpty()
        val url = URL("https://photon.komoot.io/api/?q=\$encoded&limit=16&lang=fa\$biasPart")
        val json = JSONObject(readUrl(url, "RahYar/1.6.2 Android"))
        val features = json.optJSONArray("features") ?: JSONArray()

        return buildList {
            for (i in 0 until features.length()) {
                val feature = features.optJSONObject(i) ?: continue
                val geometry = feature.optJSONObject("geometry") ?: continue
                val coordinates = geometry.optJSONArray("coordinates") ?: continue
                if (coordinates.length() < 2) continue
                val lon = coordinates.optDouble(0, Double.NaN)
                val lat = coordinates.optDouble(1, Double.NaN)
                if (!lat.isFinite() || !lon.isFinite()) continue

                val props = feature.optJSONObject("properties") ?: JSONObject()
                val title = props.optString("name").trim()
                    .ifBlank { props.optString("street").trim() }
                    .ifBlank { props.optString("city").trim() }
                    .ifBlank { continue }
                val subtitle = listOf(
                    props.optString("street"),
                    props.optString("district"),
                    props.optString("city"),
                    props.optString("state"),
                    props.optString("country")
                ).map { it.trim() }.filter { it.isNotBlank() && it != title }.distinct().joinToString("، ")

                add(
                    SearchResult(
                        id = "photon_\${props.optString("osm_type")}_\${props.optString("osm_id", i.toString())}",
                        title = title,
                        subtitle = subtitle.takeIf { it.isNotBlank() },
                        location = LatLng(lat, lon)
                    )
                )
            }
        }
    }

    private fun fetchNominatim(query: String, bias: LatLng?): List<SearchResult> {
        val encoded = URLEncoder.encode(query, Charsets.UTF_8.name())
        val viewbox = bias?.let {
            val west = it.longitude - 0.45
            val east = it.longitude + 0.45
            val north = it.latitude + 0.35
            val south = it.latitude - 0.35
            "&viewbox=\$west,\$north,\$east,\$south&bounded=0"
        }.orEmpty()
        val url = URL(
            "https://nominatim.openstreetmap.org/search" +
                "?format=jsonv2&addressdetails=1&accept-language=fa&countrycodes=ir&limit=16\$viewbox&q=\$encoded"
        )
        val array = JSONArray(readUrl(url, "RahYar/1.6.2 Android"))

        return buildList {
            for (i in 0 until array.length()) {
                val obj = array.optJSONObject(i) ?: continue
                val lat = obj.optString("lat").toDoubleOrNull() ?: continue
                val lon = obj.optString("lon").toDoubleOrNull() ?: continue
                val display = obj.optString("display_name").trim()
                val title = obj.optString("name").trim()
                    .ifBlank { display.substringBefore(',').trim() }
                    .ifBlank { continue }
                add(
                    SearchResult(
                        id = "nominatim_\${obj.optString("place_id", i.toString())}",
                        title = title,
                        subtitle = display.takeIf { it.isNotBlank() && it != title },
                        location = LatLng(lat, lon)
                    )
                )
            }
        }
    }

    private fun readUrl(url: URL, userAgent: String): String {
        val connection = (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 8000
            readTimeout = 8000
            requestMethod = "GET"
            setRequestProperty("User-Agent", userAgent)
            setRequestProperty("Accept", "application/json")
        }
        try {
            if (connection.responseCode !in 200..299) {
                error("Search HTTP \${connection.responseCode}")
            }
            return connection.inputStream.bufferedReader().use { it.readText() }
        } finally {
            connection.disconnect()
        }
    }

    private fun lastKnownBias(): LatLng? {
        val fine = appContext.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val coarse = appContext.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (!fine && !coarse) return null

        val manager = appContext.getSystemService(Context.LOCATION_SERVICE) as? LocationManager ?: return null
        val providers = listOf(
            LocationManager.GPS_PROVIDER,
            LocationManager.NETWORK_PROVIDER,
            LocationManager.PASSIVE_PROVIDER
        )
        val best = providers.mapNotNull { provider ->
            runCatching { manager.getLastKnownLocation(provider) }.getOrNull()
        }.filter { it.latitude in 24.0..40.0 && it.longitude in 43.0..64.0 }
            .maxByOrNull { it.time }
            ?: return null
        return LatLng(best.latitude, best.longitude)
    }

"""
text = text[:start] + search_impl + text[end:]
repo.write_text(text)
