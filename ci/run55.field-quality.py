from pathlib import Path
import shutil

root = Path(".")
ci = Path(__file__).resolve().parent

def copy_asset(name: str, target: str):
    src = ci / name
    dst = root / target
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)

copy_asset(
    "run55.TripTraceQuality.kt",
    "app/src/main/java/ir/rahyar/app/core/navigation/TripTraceQuality.kt"
)
copy_asset(
    "run55.TripTraceQualityTest.kt",
    "app/src/test/java/ir/rahyar/app/core/navigation/TripTraceQualityTest.kt"
)

# NavigationSession: carry horizontal accuracy and filter trace points at source.
session = root / "app/src/main/java/ir/rahyar/app/navigation/NavigationSession.kt"
s = session.read_text()
old_trace = """data class TracePoint(
    val location: GeoPoint,
    val timestampMillis: Long,
    val speedKmh: Double,
    val heading: Float
)"""
new_trace = """data class TracePoint(
    val location: GeoPoint,
    val timestampMillis: Long,
    val speedKmh: Double,
    val heading: Float,
    val accuracyMeters: Float? = null
)"""
if old_trace not in s:
    raise SystemExit("Run55 TracePoint target missing")
s = s.replace(old_trace, new_trace, 1)

if "import ir.rahyar.app.core.navigation.shouldAcceptTracePoint" not in s:
    s = s.replace(
        "import ir.rahyar.app.domain.models.*\n",
        "import ir.rahyar.app.domain.models.*\nimport ir.rahyar.app.core.navigation.shouldAcceptTracePoint\n",
        1
    )

old_append = """    fun appendTracePoint(point: TracePoint) {
        _state.update { current ->
            if (current.navigationState !is NavigationState.Navigating) current
            else current.copy(tripTrace = TripTrace(current.tripTrace.points + point))
        }
    }"""
new_append = """    fun appendTracePoint(point: TracePoint) {
        _state.update { current ->
            if (current.navigationState !is NavigationState.Navigating) {
                current
            } else {
                val previous = current.tripTrace.points.lastOrNull()
                if (!shouldAcceptTracePoint(previous, point)) {
                    current
                } else {
                    current.copy(
                        tripTrace = TripTrace(current.tripTrace.points + point)
                    )
                }
            }
        }
    }"""
if old_append not in s:
    raise SystemExit("Run55 appendTracePoint target missing")
s = s.replace(old_append, new_append, 1)
session.write_text(s)

# NavigationEngine: persist accuracy with each actual trace point.
engine = root / "app/src/main/java/ir/rahyar/app/core/navigation/NavigationEngine.kt"
e = engine.read_text()
old_engine_trace = """                speedKmh = displaySpeedKmh(signal.speedMps),
                heading = signal.bearingDegrees
            )"""
new_engine_trace = """                speedKmh = displaySpeedKmh(signal.speedMps),
                heading = signal.bearingDegrees,
                accuracyMeters = sample.horizontalAccuracyMeters.toFloat()
            )"""
if old_engine_trace not in e:
    raise SystemExit("Run55 NavigationEngine TracePoint target missing")
e = e.replace(old_engine_trace, new_engine_trace, 1)
engine.write_text(e)

# TripStory: reject non-trips and record only encountered/deduplicated conditions.
runtime = root / "app/src/main/java/ir/rahyar/app/core/navigation/TripStoryRuntime.kt"
r = runtime.read_text()

old_weather = """    fun recordWeather(info: WeatherInfo, timestampMillis: Long) {
        if (!info.isLive) return
        info.timeline.forEach { item ->
            val event = TripStoryWeatherEvent(
                timestampMillis = timestampMillis,
                location = item.location,
                summary = info.summary,
                temperatureC = item.temperatureC,
                precipitationMm = item.precipitationMm,
                hazards = item.hazards
            )
            if (weatherEvents.none {
                    it.timestampMillis == event.timestampMillis &&
                        it.location == event.location &&
                        it.temperatureC == event.temperatureC &&
                        it.hazards == event.hazards
                }) {
                weatherEvents += event
            }
        }
    }"""
new_weather = """    fun recordWeather(
        info: WeatherInfo,
        timestampMillis: Long,
        currentLocation: LatLng? = null
    ) {
        if (!info.isLive || info.timeline.isEmpty()) return
        val item = if (currentLocation == null) {
            info.timeline.first()
        } else {
            info.timeline.minByOrNull {
                traceDistanceMeters(currentLocation, it.location)
            } ?: return
        }
        val event = TripStoryWeatherEvent(
            timestampMillis = timestampMillis,
            location = currentLocation ?: item.location,
            summary = info.summary,
            temperatureC = item.temperatureC,
            precipitationMm = item.precipitationMm,
            hazards = item.hazards
        )
        val previous = weatherEvents.lastOrNull()
        val materiallyChanged = previous == null ||
            previous.summary != event.summary ||
            previous.temperatureC != event.temperatureC ||
            previous.hazards != event.hazards ||
            kotlin.math.abs(previous.precipitationMm - event.precipitationMm) >= 0.2 ||
            timestampMillis - previous.timestampMillis >= 600_000L
        if (materiallyChanged) weatherEvents += event
    }"""
if old_weather not in r:
    raise SystemExit("Run55 recordWeather target missing")
r = r.replace(old_weather, new_weather, 1)

old_traffic = """    fun recordTraffic(info: TrafficInfo, timestampMillis: Long) {
        if (!info.isLive) return
        info.segments.forEach { segment ->
            val event = TripStoryTrafficEvent(
                timestampMillis = timestampMillis,
                location = segment.start,
                level = segment.level,
                jamFactor = segment.jamFactor
            )
            if (trafficEvents.none {
                    it.timestampMillis == event.timestampMillis &&
                        it.location == event.location &&
                        it.level == event.level &&
                        it.jamFactor == event.jamFactor
                }) {
                trafficEvents += event
            }
        }
    }"""
new_traffic = """    fun recordTraffic(
        info: TrafficInfo,
        timestampMillis: Long,
        currentLocation: LatLng? = null
    ) {
        if (!info.isLive || info.segments.isEmpty()) return
        val segment = if (currentLocation == null) {
            info.segments.first()
        } else {
            info.segments.minByOrNull {
                traceDistanceMeters(currentLocation, it.start)
            } ?: return
        }
        val event = TripStoryTrafficEvent(
            timestampMillis = timestampMillis,
            location = currentLocation ?: segment.start,
            level = segment.level,
            jamFactor = segment.jamFactor
        )
        val previous = trafficEvents.lastOrNull()
        val materiallyChanged = previous == null ||
            previous.level != event.level ||
            kotlin.math.abs((previous.jamFactor ?: 0.0) - (event.jamFactor ?: 0.0)) >= 1.0 ||
            timestampMillis - previous.timestampMillis >= 300_000L
        if (materiallyChanged) trafficEvents += event
    }"""
if old_traffic not in r:
    raise SystemExit("Run55 recordTraffic target missing")
r = r.replace(old_traffic, new_traffic, 1)

old_build = """    fun build(trace: TripTrace, tripId: String? = null): TripStoryRuntimeData? {
        val summary = buildTripSummary(trace) ?: return null
        val sortedTrace = TripTrace(trace.points.sortedBy { it.timestampMillis })
        return TripStoryRuntimeData("""
new_build = """    fun build(trace: TripTrace, tripId: String? = null): TripStoryRuntimeData? {
        val sortedTrace = qualityFilteredTripTrace(trace)
        if (!isMeaningfulRealTrip(sortedTrace)) return null
        val summary = buildTripSummary(sortedTrace) ?: return null
        return TripStoryRuntimeData("""
if old_build not in r:
    raise SystemExit("Run55 TripStory build target missing")
r = r.replace(old_build, new_build, 1)
runtime.write_text(r)

# Add field-regression tests to TripStoryRuntimeTest.
runtime_test = root / "app/src/test/java/ir/rahyar/app/core/navigation/TripStoryRuntimeTest.kt"
rt = runtime_test.read_text()
insert_before = "\n    @Test fun driverAerialAndOverviewExposeDifferentTraceWindows() {"
extra = """
    @Test fun zeroDistanceOneMinuteGpsJitterCannotBuildStory() {
        val jitter = TripTrace(
            (0..12).map { i ->
                TracePoint(
                    location = LatLng(
                        35.7000 + (if (i % 2 == 0) 0.000015 else -0.000015),
                        51.4000 + (if (i % 3 == 0) 0.000015 else -0.000010)
                    ),
                    timestampMillis = i * 5_000L,
                    speedKmh = 2.0,
                    heading = 0f,
                    accuracyMeters = 18f
                )
            }
        )
        assertNull(TripStoryRecorder().build(jitter))
    }

    @Test fun identicalWeatherSamplesDoNotSpamTimeline() {
        val snapshot = RouteWeatherSnapshot(
            location = LatLng(35.7, 51.4),
            temperatureC = 22,
            weatherCode = 0,
            precipitationMm = 0.0,
            windSpeedKmh = 5.0,
            hazards = emptySet()
        )
        val info = WeatherInfo(
            summary = "صاف • ۲۲°",
            alerts = emptyList(),
            isLive = true,
            timeline = listOf(
                snapshot,
                snapshot.copy(location = LatLng(35.71, 51.41))
            )
        )
        val recorder = TripStoryRecorder()
        recorder.recordWeather(info, 60_000L, LatLng(35.7001, 51.4001))
        recorder.recordWeather(info, 120_000L, LatLng(35.7002, 51.4002))
        val story = recorder.build(trace())!!
        assertEquals(1, story.weatherTimeline.size)
    }

"""
if "zeroDistanceOneMinuteGpsJitterCannotBuildStory" not in rt:
    if insert_before not in rt:
        raise SystemExit("Run55 TripStory test insertion target missing")
    rt = rt.replace(insert_before, "\n" + extra + "    @Test fun driverAerialAndOverviewExposeDifferentTraceWindows() {", 1)
runtime_test.write_text(rt)

# ActiveNavigation: dark-state contrast, encountered context, unmistakable car, numbered stops.
active = root / "app/src/main/java/ir/rahyar/app/ui/screens/ActiveNavigationScreen.kt"
a = active.read_text()

old_error = """    if (route == null || destination == null) {
        Column(Modifier.fillMaxSize().padding(24.dp)) {
            Text("مسیر فعال در دسترس نیست", style = MaterialTheme.typography.titleLarge)
            Spacer(Modifier.height(12.dp))
            Button(onClick = { navController.popBackStack() }) {
                Text("بازگشت")
            }
        }
        return
    }"""
new_error = """    if (route == null || destination == null) {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = MaterialTheme.colorScheme.background,
            contentColor = MaterialTheme.colorScheme.onBackground
        ) {
            Column(Modifier.fillMaxSize().padding(24.dp)) {
                Text(
                    "مسیر فعال در دسترس نیست",
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onBackground
                )
                Spacer(Modifier.height(12.dp))
                Button(onClick = { navController.popBackStack() }) {
                    Text("بازگشت")
                }
            }
        }
        return
    }"""
if old_error not in a:
    raise SystemExit("Run55 route unavailable target missing")
a = a.replace(old_error, new_error, 1)

if "tripStoryRecorder.recordWeather(it, System.currentTimeMillis())" not in a:
    raise SystemExit("Run55 weather recorder call missing")
a = a.replace(
    "tripStoryRecorder.recordWeather(it, System.currentTimeMillis())",
    "tripStoryRecorder.recordWeather(it, System.currentTimeMillis(), active?.currentLocation)",
    1
)
if "tripStoryRecorder.recordTraffic(it, System.currentTimeMillis())" not in a:
    raise SystemExit("Run55 traffic recorder call missing")
a = a.replace(
    "tripStoryRecorder.recordTraffic(it, System.currentTimeMillis())",
    "tripStoryRecorder.recordTraffic(it, System.currentTimeMillis(), active?.currentLocation)",
    1
)

stop_start = a.find(
    "        val icon = runCatching { IconFactory.getInstance(context).fromResource(R.drawable.ic_stop_marker) }.getOrNull()"
)
stop_end_marker = "\n    LaunchedEffect(mapRef, active?.roadEvents)"
stop_end = a.find(stop_end_marker, stop_start)
if stop_start < 0 or stop_end < 0:
    raise SystemExit("Run55 stop marker target missing")
new_stop = """        stopMarkers = session.itinerary?.stops.orEmpty()
            .filter { it.status != ir.rahyar.app.domain.models.StopStatus.SKIPPED }
            .sortedBy { it.order }
            .map { stop ->
                val arrived =
                    stop.status == ir.rahyar.app.domain.models.StopStatus.ARRIVED
                val icon = runCatching {
                    IconFactory.getInstance(context).fromBitmap(
                        numberedStopBitmap(stop.order, arrived)
                    )
                }.getOrNull()
                val options = MarkerOptions()
                    .position(MapLatLng(stop.location.latitude, stop.location.longitude))
                    .title("توقف " + faNumber(stop.order))
                    .snippet(if (arrived) "انجام شد" else "در انتظار")
                icon?.let(options::icon)
                map.addMarker(options)
            }
"""
a = a[:stop_start] + new_stop + a[stop_end:]

old_vehicle = """    if (style.getImage(VEHICLE_IMAGE_ID) == null) {
        drawableBitmap(context, R.drawable.ic_vehicle_marker)?.let { bitmap ->
            style.addImage(VEHICLE_IMAGE_ID, bitmap)
        }
    }"""
new_vehicle = """    if (style.getImage(VEHICLE_IMAGE_ID) == null) {
        val bitmap = runCatching { navigationVehicleBitmap() }.getOrNull()
            ?: drawableBitmap(context, R.drawable.ic_vehicle_marker)
        bitmap?.let { style.addImage(VEHICLE_IMAGE_ID, it) }
    }"""
if old_vehicle not in a:
    raise SystemExit("Run55 vehicle bitmap target missing")
a = a.replace(old_vehicle, new_vehicle, 1)
a = a.replace("iconSize(0.78f)", "iconSize(1.05f)", 1)

anchor = "private fun drawableBitmap(context: android.content.Context, resId: Int): Bitmap? {\n"
helpers = """private fun navigationVehicleBitmap(): Bitmap {
    val width = 72
    val height = 96
    val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)

    val body = android.graphics.Path().apply {
        moveTo(width / 2f, 3f)
        lineTo(63f, 28f)
        lineTo(60f, 80f)
        lineTo(48f, 91f)
        lineTo(24f, 91f)
        lineTo(12f, 80f)
        lineTo(9f, 28f)
        close()
    }
    val fill = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
        style = android.graphics.Paint.Style.FILL
        color = AndroidColor.parseColor("#008E95")
    }
    val border = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
        style = android.graphics.Paint.Style.STROKE
        strokeWidth = 5f
        strokeJoin = android.graphics.Paint.Join.ROUND
        color = AndroidColor.WHITE
    }
    canvas.drawPath(body, fill)
    canvas.drawPath(body, border)

    val windshield = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
        style = android.graphics.Paint.Style.FILL
        color = AndroidColor.parseColor("#092A35")
    }
    canvas.drawRoundRect(22f, 34f, 50f, 55f, 7f, 7f, windshield)

    val lamp = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
        style = android.graphics.Paint.Style.FILL
        color = AndroidColor.WHITE
    }
    canvas.drawCircle(22f, 71f, 4f, lamp)
    canvas.drawCircle(50f, 71f, 4f, lamp)
    return bitmap
}

private fun numberedStopBitmap(order: Int, arrived: Boolean): Bitmap {
    val size = 64
    val bitmap = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888)
    val canvas = Canvas(bitmap)
    val fill = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
        style = android.graphics.Paint.Style.FILL
        color = AndroidColor.parseColor(if (arrived) "#16A34A" else "#7C3AED")
    }
    val stroke = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
        style = android.graphics.Paint.Style.STROKE
        strokeWidth = 5f
        color = AndroidColor.WHITE
    }
    canvas.drawCircle(size / 2f, size / 2f, 26f, fill)
    canvas.drawCircle(size / 2f, size / 2f, 26f, stroke)

    val textPaint = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
        style = android.graphics.Paint.Style.FILL
        color = AndroidColor.WHITE
        textSize = 28f
        textAlign = android.graphics.Paint.Align.CENTER
        typeface = android.graphics.Typeface.DEFAULT_BOLD
    }
    val baseline = size / 2f - (textPaint.ascent() + textPaint.descent()) / 2f
    canvas.drawText(order.toString(), size / 2f, baseline, textPaint)
    return bitmap
}

"""
if anchor not in a:
    raise SystemExit("Run55 bitmap helper anchor missing")
a = a.replace(anchor, helpers + anchor, 1)
active.write_text(a)
