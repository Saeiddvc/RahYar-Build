from pathlib import Path
import shutil

root = Path(".")

def copy_asset(name, target):
    src = Path(__file__).resolve().parent / name
    dst = root / target
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)

copy_asset(
    "run52.TripStoryRuntime.kt",
    "app/src/main/java/ir/rahyar/app/core/navigation/TripStoryRuntime.kt"
)
copy_asset(
    "run52.TripStoryRuntimeTest.kt",
    "app/src/test/java/ir/rahyar/app/core/navigation/TripStoryRuntimeTest.kt"
)
copy_asset(
    "run52.TripStoryMotionView.kt",
    "app/src/main/java/ir/rahyar/app/ui/components/TripStoryMotionView.kt"
)
copy_asset(
    "run52.TripStoryStore.kt",
    "app/src/main/java/ir/rahyar/app/data/trip/TripStoryStore.kt"
)

nav_host = root / "app/src/main/java/ir/rahyar/app/navigation/RahyarNavHost.kt"
nh = nav_host.read_text()
target = """                weatherRepository = weatherRepository,
                navigationSession = navigationSession"""
replacement = """                weatherRepository = weatherRepository,
                trafficRepository = trafficRepository,
                navigationSession = navigationSession"""
if target not in nh:
    raise SystemExit("Run52 RahyarNavHost traffic target missing")
nh = nh.replace(target, replacement, 1)
nav_host.write_text(nh)

active = root / "app/src/main/java/ir/rahyar/app/ui/screens/ActiveNavigationScreen.kt"
a = active.read_text()

a = a.replace(
    "import ir.rahyar.app.core.navigation.buildTripStoryPayload\n",
    ""
)

new_imports = """import ir.rahyar.app.core.navigation.TripStoryRecorder
import ir.rahyar.app.core.navigation.TripStoryRuntimeData
import ir.rahyar.app.core.navigation.buildTripStoryTimeline
import ir.rahyar.app.domain.models.StopStatus
import ir.rahyar.app.domain.models.TrafficInfo
import ir.rahyar.app.domain.models.TripMediaType
import ir.rahyar.app.domain.repository.TrafficRepository
import ir.rahyar.app.ui.components.TripStoryMotionView
"""
anchor = "import ir.rahyar.app.navigation.NavigationSession\n"
if anchor not in a:
    raise SystemExit("Run52 import anchor missing")
if "import ir.rahyar.app.core.navigation.TripStoryRecorder\n" not in a:
    a = a.replace(anchor, new_imports + anchor, 1)

sig = """    roadAwarenessRepository: RoadAwarenessRepository,
    weatherRepository: WeatherRepository,
    navigationSession: NavigationSession"""
rep = """    roadAwarenessRepository: RoadAwarenessRepository,
    weatherRepository: WeatherRepository,
    trafficRepository: TrafficRepository,
    navigationSession: NavigationSession"""
if a.count(sig) < 2:
    raise SystemExit("Run52 expected two ActiveNavigation signatures")
a = a.replace(sig, rep)

call = """        roadAwarenessRepository = roadAwarenessRepository,
        weatherRepository = weatherRepository,
        navigationSession = navigationSession,"""
rep_call = """        roadAwarenessRepository = roadAwarenessRepository,
        weatherRepository = weatherRepository,
        trafficRepository = trafficRepository,
        navigationSession = navigationSession,"""
if call not in a:
    raise SystemExit("Run52 NavigationHUDScreen traffic call missing")
a = a.replace(call, rep_call, 1)

state_anchor = """    var liveWeather by remember { mutableStateOf<WeatherInfo?>(null) }
    var lastSpokenWeatherAlert by remember { mutableStateOf<String?>(null) }"""
state_replacement = state_anchor + """
    var liveTraffic by remember { mutableStateOf<TrafficInfo?>(null) }
    val tripStoryRecorder = remember { TripStoryRecorder() }
    var completedTripStory by remember { mutableStateOf<TripStoryRuntimeData?>(null) }"""
if state_anchor not in a:
    raise SystemExit("Run52 state anchor missing")
a = a.replace(state_anchor, state_replacement, 1)

permission_end = """    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        permissionGranted =
            result[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
                result[Manifest.permission.ACCESS_COARSE_LOCATION] == true
    }
"""
media_launcher = permission_end + """
    val tripMediaPicker = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri ->
        val location = active?.currentLocation
            ?: navigationSession.state.value.tripTrace.points.lastOrNull()?.location
        if (uri != null && location != null) {
            tripStoryRecorder.recordMedia(
                uri = uri.toString(),
                type = TripMediaType.PHOTO,
                timestampMillis = System.currentTimeMillis(),
                location = location
            )
        }
    }
"""
if permission_end not in a:
    raise SystemExit("Run52 media launcher anchor missing")
a = a.replace(permission_end, media_launcher, 1)

weather_old = """    LaunchedEffect(active?.route?.id) {
        if (active == null) {
            liveWeather = null
            return@LaunchedEffect
        }
        while (true) {
            val currentRoute = (engine.hudState.value as? NavigationHudState.Active)?.route ?: initialRoute
            liveWeather = runCatching { weatherRepository.getWeatherAlongRoute(currentRoute) }
                .getOrNull()
                ?.takeIf { it.isLive }
            delay(300_000L)
        }
    }
"""
weather_new = """    LaunchedEffect(active?.route?.id) {
        if (active == null) {
            liveWeather = null
            return@LaunchedEffect
        }
        while (true) {
            val currentRoute = (engine.hudState.value as? NavigationHudState.Active)?.route ?: initialRoute
            val weather = runCatching { weatherRepository.getWeatherAlongRoute(currentRoute) }
                .getOrNull()
                ?.takeIf { it.isLive }
            liveWeather = weather
            weather?.let {
                tripStoryRecorder.recordWeather(it, System.currentTimeMillis())
            }
            delay(300_000L)
        }
    }

    LaunchedEffect(active?.route?.id) {
        if (active == null) {
            liveTraffic = null
            return@LaunchedEffect
        }
        while (true) {
            val currentRoute = (engine.hudState.value as? NavigationHudState.Active)?.route ?: initialRoute
            val traffic = runCatching { trafficRepository.getTrafficForRoute(currentRoute) }
                .getOrNull()
                ?.takeIf { it.isLive }
            liveTraffic = traffic
            traffic?.let {
                tripStoryRecorder.recordTraffic(it, System.currentTimeMillis())
            }
            delay(120_000L)
        }
    }

    LaunchedEffect(
        session.itinerary?.stops?.map { it.id + ":" + it.status.name }
    ) {
        session.itinerary?.stops
            .orEmpty()
            .filter { it.status == StopStatus.ARRIVED }
            .forEach { stop ->
                tripStoryRecorder.recordStop(
                    id = stop.id,
                    timestampMillis = System.currentTimeMillis(),
                    location = stop.location
                )
            }
    }
"""
if weather_old not in a:
    raise SystemExit("Run52 weather runtime anchor missing")
a = a.replace(weather_old, weather_new, 1)

quick_anchor = """                QuickToggle("هشدار محدودیت سرعت", quickSettings.speedLimitAlertsEnabled) { value -> navigationSession.updateQuickSettings { it.copy(speedLimitAlertsEnabled = value) } }
                if (!voiceAvailable) Text("صدای فارسی سازگار روی دستگاه در دسترس نیست", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(12.dp))"""
quick_new = """                QuickToggle("هشدار محدودیت سرعت", quickSettings.speedLimitAlertsEnabled) { value -> navigationSession.updateQuickSettings { it.copy(speedLimitAlertsEnabled = value) } }
                Button(
                    modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                    onClick = { tripMediaPicker.launch("image/*") }
                ) {
                    Text("افزودن عکس واقعی به تریپ‌استوری")
                }
                if (!voiceAvailable) Text("صدای فارسی سازگار روی دستگاه در دسترس نیست", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(12.dp))"""
if quick_anchor not in a:
    raise SystemExit("Run52 Quick Settings media anchor missing")
a = a.replace(quick_anchor, quick_new, 1)

end_anchor = """                        endedSnapshot = active
                        tripEndedAtMillis = System.currentTimeMillis()
                        navigationSession.endTrip()
                        engine.stopNavigation()"""
end_new = """                        endedSnapshot = active
                        tripEndedAtMillis = System.currentTimeMillis()
                        completedTripStory = tripStoryRecorder.build(
                            trace = session.tripTrace,
                            tripId = session.sessionId
                        )
                        navigationSession.endTrip()
                        engine.stopNavigation()"""
if end_anchor not in a:
    raise SystemExit("Run52 end-trip snapshot anchor missing")
a = a.replace(end_anchor, end_new, 1)

start = a.find("    if (showTripStory) {")
marker = "@Composable\nprivate fun QuickToggle("
end = a.find(marker, start)
if start < 0 or end < 0:
    raise SystemExit("Run52 TripStory tail markers missing")

new_tail = """    if (showTripStory) {
        TripStorySheet(
            story = completedTripStory,
            rerouteCount = endedSnapshot?.rerouteCount ?: 0,
            onFinish = { rating ->
                completedTripStory?.let { story ->
                    TripStoryStore.save(
                        context = context,
                        record = TripStoryRecord(
                            tripId = story.tripId,
                            startedAtMillis = story.trace.points.first().timestampMillis,
                            endedAtMillis = story.trace.points.last().timestampMillis,
                            actualDistanceKm = story.actualDistanceMeters / 1000.0,
                            actualDurationMinutes = (story.actualDurationMillis / 60_000L).toInt(),
                            averageSpeedKmh = story.averageSpeedKmh,
                            maxSpeedKmh = story.maxSpeedKmh,
                            rerouteCount = endedSnapshot?.rerouteCount ?: 0,
                            stopCount = story.stopTimeline.size,
                            mediaCount = story.mediaTimeline.size,
                            weatherEventCount = story.weatherTimeline.size,
                            trafficEventCount = story.trafficTimeline.size,
                            navigationRating = rating
                        )
                    )
                }
                showTripStory = false
                onStop()
            }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun TripStorySheet(
    story: TripStoryRuntimeData?,
    rerouteCount: Int,
    onFinish: (Int?) -> Unit
) {
    var rating by remember { mutableStateOf<Int?>(null) }

    ModalBottomSheet(onDismissRequest = {}) {
        Column(
            Modifier
                .fillMaxWidth()
                .navigationBarsPadding()
                .padding(horizontal = 20.dp, vertical = 12.dp)
        ) {
            Text("تریپ‌استوری", style = MaterialTheme.typography.titleLarge)
            Spacer(Modifier.height(8.dp))

            if (story == null) {
                Text(
                    "داده سفر واقعی برای ساخت Trip Story وجود ندارد.",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.error
                )
            } else {
                TripStoryMotionView(
                    story = story,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(Modifier.height(10.dp))
                Text(
                    "مسافت واقعی: " + faDistance(story.actualDistanceMeters / 1000.0) + " کیلومتر",
                    style = MaterialTheme.typography.bodyMedium
                )
                Text(
                    "زمان واقعی سفر: " + faNumber((story.actualDurationMillis / 60_000L).toInt()) + " دقیقه",
                    style = MaterialTheme.typography.bodyMedium
                )
                Text(
                    "میانگین سرعت واقعی: " + faNumber(story.averageSpeedKmh.roundToInt()) + " کیلومتر/ساعت",
                    style = MaterialTheme.typography.bodyMedium
                )
                Text(
                    "بیشترین سرعت واقعی: " + faNumber(story.maxSpeedKmh.roundToInt()) + " کیلومتر/ساعت",
                    style = MaterialTheme.typography.bodyMedium
                )
                Text(
                    "بازمحاسبه مسیر: " + faNumber(rerouteCount) +
                        " بار • توقف‌های واقعی: " + faNumber(story.stopTimeline.size),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                val timeline = buildTripStoryTimeline(story)
                if (timeline.isNotEmpty()) {
                    Spacer(Modifier.height(10.dp))
                    Text("خط زمانی واقعی سفر", style = MaterialTheme.typography.titleMedium)
                    timeline.takeLast(10).forEach { item ->
                        Text(
                            text = "• " + item.description,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
                if (story.mediaTimeline.isNotEmpty()) {
                    Text(
                        "رسانه‌های واقعی سفر: " + faNumber(story.mediaTimeline.size),
                        style = MaterialTheme.typography.bodySmall
                    )
                }
                if (story.weatherTimeline.isEmpty()) {
                    Text(
                        "داده زنده آب‌وهوا در این سفر ثبت نشد.",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
                if (story.trafficTimeline.isEmpty()) {
                    Text(
                        "داده زنده ترافیک در این سفر ثبت نشد.",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }

            Spacer(Modifier.height(16.dp))
            Text(
                "کیفیت مسیریابی راه‌یار چطور بود؟",
                style = MaterialTheme.typography.titleMedium
            )
            Spacer(Modifier.height(8.dp))
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                (1..5).forEach { value ->
                    FilterChip(
                        selected = rating == value,
                        onClick = { rating = value },
                        label = { Text(faNumber(value)) }
                    )
                }
            }

            Spacer(Modifier.height(14.dp))
            Button(
                modifier = Modifier.fillMaxWidth(),
                onClick = { onFinish(rating) }
            ) {
                Text("ثبت تریپ‌استوری و پایان")
            }
            TextButton(
                modifier = Modifier.fillMaxWidth(),
                onClick = { onFinish(null) }
            ) {
                Text("فعلاً بدون امتیاز پایان بده")
            }
        }
    }
}

"""
a = a[:start] + new_tail + a[end:]
active.write_text(a)
