package ir.rahyar.app.core.home

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.SearchResult
import ir.rahyar.app.domain.models.TrafficInfo
import ir.rahyar.app.domain.models.TrafficLevel
import ir.rahyar.app.domain.models.TrafficSegment
import ir.rahyar.app.domain.models.WeatherInfo
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class HomeDashboardContractTest {
    @Test
    fun requiredServiceShortcutsAreComplete() {
        assertEquals(
            setOf(
                HomeServiceType.FUEL,
                HomeServiceType.REST_AREA,
                HomeServiceType.FOOD_CAFE,
                HomeServiceType.TOILET,
                HomeServiceType.PARKING,
                HomeServiceType.HOSPITAL,
                HomeServiceType.TOURISM
            ),
            requiredHomeServiceShortcuts.map { it.type }.toSet()
        )
    }

    @Test
    fun remoteServiceResultsAreRejectedFromHome() {
        val current = LatLng(35.83, 50.99)
        val near = SearchResult(
            "near",
            "پمپ بنزین نزدیک",
            "کرج",
            LatLng(35.82, 50.98)
        )
        val remote = SearchResult(
            "remote",
            "پمپ بنزین دور",
            "کرمان",
            LatLng(30.28, 57.08)
        )

        assertEquals(
            listOf("near"),
            filterHomeServiceResults(
                listOf(remote, near),
                current
            ).map { it.id }
        )
    }

    @Test
    fun unavailableProvidersAreNeverShownAsLiveStatus() {
        assertTrue(
            weatherStatusLabel(
                WeatherInfo(
                    summary = "نامعتبر",
                    alerts = emptyList(),
                    isLive = false
                )
            ).contains("در دسترس نیست")
        )
        assertTrue(
            trafficStatusLabel(
                TrafficInfo(
                    segments = emptyList(),
                    isLive = false
                )
            ).contains("در دسترس نیست")
        )
    }

    @Test
    fun liveWeatherAndHeavyTrafficAreVisible() {
        assertTrue(
            weatherStatusLabel(
                WeatherInfo(
                    summary = "بارانی",
                    alerts = listOf("بارش"),
                    isLive = true
                )
            ).contains("بارانی")
        )

        val traffic = TrafficInfo(
            segments = listOf(
                TrafficSegment(
                    start = LatLng(35.8, 51.0),
                    end = LatLng(35.81, 51.01),
                    level = TrafficLevel.HEAVY,
                    jamFactor = 8.0
                )
            ),
            isLive = true
        )
        assertTrue(trafficStatusLabel(traffic).contains("سنگین"))
        assertFalse(trafficStatusLabel(traffic).contains("در دسترس نیست"))
    }
}
