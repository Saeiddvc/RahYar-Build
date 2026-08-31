package ir.rahyar.app.core.home

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.SearchResult
import ir.rahyar.app.domain.models.TrafficInfo
import ir.rahyar.app.domain.models.TrafficLevel
import ir.rahyar.app.domain.models.WeatherInfo
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

enum class HomeServiceType {
    FUEL,
    REST_AREA,
    FOOD_CAFE,
    TOILET,
    PARKING,
    HOSPITAL,
    TOURISM
}

data class HomeServiceShortcut(
    val type: HomeServiceType,
    val label: String,
    val query: String
)

val requiredHomeServiceShortcuts: List<HomeServiceShortcut> = listOf(
    HomeServiceShortcut(HomeServiceType.FUEL, "سوخت", "پمپ بنزین"),
    HomeServiceShortcut(HomeServiceType.REST_AREA, "مجتمع بین‌راهی", "مجتمع خدماتی رفاهی"),
    HomeServiceShortcut(HomeServiceType.FOOD_CAFE, "غذا و کافه", "رستوران کافه"),
    HomeServiceShortcut(HomeServiceType.TOILET, "سرویس بهداشتی", "سرویس بهداشتی عمومی"),
    HomeServiceShortcut(HomeServiceType.PARKING, "پارکینگ", "پارکینگ"),
    HomeServiceShortcut(HomeServiceType.HOSPITAL, "بیمارستان", "بیمارستان"),
    HomeServiceShortcut(HomeServiceType.TOURISM, "گردشگری", "جاذبه گردشگری")
)

fun filterHomeServiceResults(
    results: List<SearchResult>,
    currentLocation: LatLng?,
    maxDistanceKm: Double = 30.0
): List<SearchResult> {
    if (currentLocation == null) return results.take(8)
    return results
        .map { it to geoDistanceKm(currentLocation, it.location) }
        .filter { (_, distanceKm) -> distanceKm <= maxDistanceKm }
        .sortedBy { (_, distanceKm) -> distanceKm }
        .take(8)
        .map { it.first }
}

fun weatherStatusLabel(info: WeatherInfo?): String =
    if (info != null && info.isLive) "آب‌وهوا: " + info.summary
    else "آب‌وهوا: داده زنده در دسترس نیست"

fun trafficStatusLabel(info: TrafficInfo?): String {
    if (info == null || !info.isLive) return "ترافیک: داده زنده در دسترس نیست"
    return when {
        info.segments.any { it.level == TrafficLevel.HEAVY } -> "ترافیک: سنگین در محدوده"
        info.segments.any { it.level == TrafficLevel.MEDIUM } -> "ترافیک: متوسط"
        info.segments.any { it.level == TrafficLevel.LIGHT } -> "ترافیک: روان"
        else -> "ترافیک: داده زنده بدون طبقه‌بندی"
    }
}

private fun geoDistanceKm(a: LatLng, b: LatLng): Double {
    val radiusKm = 6_371.0
    val dLat = Math.toRadians(b.latitude - a.latitude)
    val dLon = Math.toRadians(b.longitude - a.longitude)
    val lat1 = Math.toRadians(a.latitude)
    val lat2 = Math.toRadians(b.latitude)
    val h = sin(dLat / 2) * sin(dLat / 2) +
        cos(lat1) * cos(lat2) * sin(dLon / 2) * sin(dLon / 2)
    return radiusKm * 2 * atan2(sqrt(h), sqrt(1 - h))
}
