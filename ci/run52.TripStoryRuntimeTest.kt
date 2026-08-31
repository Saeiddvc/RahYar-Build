package ir.rahyar.app.core.navigation

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.RouteWeatherSnapshot
import ir.rahyar.app.domain.models.TrafficInfo
import ir.rahyar.app.domain.models.TrafficLevel
import ir.rahyar.app.domain.models.TrafficSegment
import ir.rahyar.app.domain.models.TripMediaType
import ir.rahyar.app.domain.models.WeatherHazard
import ir.rahyar.app.domain.models.WeatherInfo
import ir.rahyar.app.navigation.TracePoint
import ir.rahyar.app.navigation.TripTrace
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class TripStoryRuntimeTest {
    private fun trace() = TripTrace(
        listOf(
            TracePoint(LatLng(35.7000, 51.4000), 1_000L, 30.0, 90f),
            TracePoint(LatLng(35.7005, 51.4010), 61_000L, 40.0, 95f),
            TracePoint(LatLng(35.7010, 51.4020), 121_000L, 50.0, 100f)
        )
    )

    @Test fun onlyRealTripTraceCanBuildStory() {
        val recorder = TripStoryRecorder()
        assertNull(recorder.build(TripTrace()))
        assertNull(
            recorder.build(
                TripTrace(listOf(TracePoint(LatLng(35.7, 51.4), 1_000L, 0.0, 0f)))
            )
        )
        assertNotNull(recorder.build(trace()))
    }

    @Test fun noTripMeansNoStoryPayload() {
        assertNull(TripStoryRecorder().build(TripTrace()))
    }

    @Test fun selectedRealMediaAppearsInTimeline() {
        val recorder = TripStoryRecorder()
        assertFalse(
            recorder.recordMedia(
                "",
                TripMediaType.PHOTO,
                60_000L,
                LatLng(35.7, 51.4)
            )
        )
        assertTrue(
            recorder.recordMedia(
                "content://photos/42",
                TripMediaType.PHOTO,
                60_000L,
                LatLng(35.7, 51.4)
            )
        )
        val story = recorder.build(trace())!!
        val media = buildTripStoryTimeline(story)
            .single { it.kind == TripStoryTimelineKind.MEDIA }
        assertEquals("content://photos/42", media.mediaUri)
    }

    @Test fun weatherTimelineAcceptsLiveProviderDataOnly() {
        val snapshot = RouteWeatherSnapshot(
            location = LatLng(35.7, 51.4),
            temperatureC = 12,
            weatherCode = 61,
            precipitationMm = 1.2,
            windSpeedKmh = 10.0,
            hazards = setOf(WeatherHazard.RAIN)
        )
        val recorder = TripStoryRecorder()
        recorder.recordWeather(
            WeatherInfo("غیرزنده", emptyList(), isLive = false, timeline = listOf(snapshot)),
            60_000L
        )
        recorder.recordWeather(
            WeatherInfo("بارانی", listOf("بارش"), isLive = true, timeline = listOf(snapshot)),
            61_000L
        )
        val story = recorder.build(trace())!!
        assertEquals(1, story.weatherTimeline.size)
        assertEquals("بارانی", story.weatherTimeline.single().summary)
    }

    @Test fun trafficTimelineAcceptsLiveProviderDataOnly() {
        val segment = TrafficSegment(
            start = LatLng(35.7, 51.4),
            end = LatLng(35.7, 51.41),
            level = TrafficLevel.HEAVY,
            jamFactor = 8.0
        )
        val recorder = TripStoryRecorder()
        recorder.recordTraffic(TrafficInfo(listOf(segment), isLive = false), 60_000L)
        recorder.recordTraffic(TrafficInfo(listOf(segment), isLive = true), 61_000L)
        val story = recorder.build(trace())!!
        assertEquals(1, story.trafficTimeline.size)
        assertEquals(TrafficLevel.HEAVY, story.trafficTimeline.single().level)
    }

    @Test fun threeViewModesHaveDistinctMotionPolicies() {
        val story = TripStoryRecorder().build(trace())!!
        assertEquals(
            setOf(
                TripStoryViewMode.DRIVER,
                TripStoryViewMode.AERIAL,
                TripStoryViewMode.OVERVIEW
            ),
            TripStoryViewMode.values().toSet()
        )
        val driver = tripStoryMotionFrame(story, TripStoryViewMode.DRIVER, 0.5f)!!
        val aerial = tripStoryMotionFrame(story, TripStoryViewMode.AERIAL, 0.5f)!!
        val overview = tripStoryMotionFrame(story, TripStoryViewMode.OVERVIEW, 0.5f)!!
        assertTrue(driver.zoom > aerial.zoom)
        assertTrue(aerial.zoom > overview.zoom)
        assertTrue(driver.tilt > aerial.tilt)
        assertEquals(0.0, overview.tilt, 0.01)
    }

    @Test fun realEffectsOnlyNeverInventWeatherTrafficOrMedia() {
        val emptyStory = TripStoryRecorder().build(trace())!!
        assertTrue(tripStoryEffectsAt(emptyStory, 61_000L).isEmpty())

        val recorder = TripStoryRecorder()
        recorder.recordWeather(
            WeatherInfo(
                summary = "بارانی",
                alerts = listOf("بارش"),
                isLive = true,
                timeline = listOf(
                    RouteWeatherSnapshot(
                        location = LatLng(35.7, 51.4),
                        temperatureC = 12,
                        weatherCode = 61,
                        precipitationMm = 1.0,
                        windSpeedKmh = 8.0,
                        hazards = setOf(WeatherHazard.RAIN)
                    )
                )
            ),
            61_000L
        )
        recorder.recordTraffic(
            TrafficInfo(
                segments = listOf(
                    TrafficSegment(
                        LatLng(35.7, 51.4),
                        LatLng(35.7, 51.41),
                        TrafficLevel.HEAVY,
                        9.0
                    )
                ),
                isLive = true
            ),
            61_000L
        )
        recorder.recordMedia(
            "content://photos/9",
            TripMediaType.PHOTO,
            61_000L,
            LatLng(35.7, 51.4)
        )
        val story = recorder.build(trace())!!
        val effects = tripStoryEffectsAt(story, 61_000L)
        assertTrue(TripStoryEffectKind.RAIN in effects)
        assertTrue(TripStoryEffectKind.HEAVY_TRAFFIC in effects)
        assertTrue(TripStoryEffectKind.MEDIA_MOMENT in effects)
    }

    @Test fun driverAerialAndOverviewExposeDifferentTraceWindows() {
        val manyPoints = TripTrace(
            (0..100).map { i ->
                TracePoint(
                    LatLng(35.7 + i * 0.0001, 51.4),
                    i * 1_000L,
                    40.0,
                    0f
                )
            }
        )
        val story = TripStoryRecorder().build(manyPoints)!!
        val driver = tripStoryVisibleTrace(story, TripStoryViewMode.DRIVER, 0.5f)
        val aerial = tripStoryVisibleTrace(story, TripStoryViewMode.AERIAL, 0.5f)
        val overview = tripStoryVisibleTrace(story, TripStoryViewMode.OVERVIEW, 0.5f)
        assertTrue(driver.size < aerial.size)
        assertTrue(aerial.size < overview.size)
    }
}
