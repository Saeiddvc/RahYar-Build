from pathlib import Path

root = Path(".")

policy = root / "app/src/main/java/ir/rahyar/app/core/navigation/RoutePreviewSafety.kt"
policy.write_text("""package ir.rahyar.app.core.navigation

import ir.rahyar.app.domain.models.CameraPadding
import ir.rahyar.app.domain.models.Route
import ir.rahyar.app.domain.models.RouteType

fun isRenderableRoute(route: Route): Boolean =
    route.points.size >= 2 &&
        route.distanceKm.isFinite() &&
        route.distanceKm > 0.0 &&
        route.durationMinutes > 0 &&
        route.points.all { it.latitude.isFinite() && it.longitude.isFinite() }

fun selectRoutePreviewRoutes(routes: List<Route>): List<Route> {
    val valid = routes.filter(::isRenderableRoute).distinctBy { it.id }
    if (valid.isEmpty()) return emptyList()

    val primary = valid.firstOrNull { it.type == RouteType.RECOMMENDED }
        ?: valid.minByOrNull { it.durationMinutes }
        ?: return emptyList()

    return listOf(primary) +
        valid.asSequence()
            .filterNot { it.id == primary.id }
            .sortedBy { it.durationMinutes }
            .take(2)
            .toList()
}

fun routePreviewCameraPadding(
    routeSheetVisible: Boolean,
    stickyStartVisible: Boolean
): CameraPadding = CameraPadding(
    top = 150,
    bottom = when {
        routeSheetVisible -> 360
        stickyStartVisible -> 220
        else -> 72
    },
    start = 28,
    end = 28
)

data class RoutePreviewCameraFitKey(
    val routeIds: String,
    val overviewRequestToken: Int
)

fun routePreviewCameraFitKey(
    routes: List<Route>,
    overviewRequestToken: Int
): RoutePreviewCameraFitKey = RoutePreviewCameraFitKey(
    routeIds = selectRoutePreviewRoutes(routes).joinToString("|") { it.id },
    overviewRequestToken = overviewRequestToken
)

fun shouldShowStickyStart(
    selectedRoute: Route?,
    blockingOverlayVisible: Boolean
): Boolean = selectedRoute != null &&
    isRenderableRoute(selectedRoute) &&
    !blockingOverlayVisible

class StartNavigationGate(
    private val debounceMillis: Long = 1_200L
) {
    private var lastAcceptedAtMillis: Long? = null

    @Synchronized
    fun tryAcquire(nowMillis: Long): Boolean {
        val previous = lastAcceptedAtMillis
        if (previous != null && nowMillis - previous in 0 until debounceMillis) return false
        lastAcceptedAtMillis = nowMillis
        return true
    }

    @Synchronized
    fun reset() {
        lastAcceptedAtMillis = null
    }
}
""")

test = root / "app/src/test/java/ir/rahyar/app/core/navigation/RoutePreviewSafetyTest.kt"
test.parent.mkdir(parents=True, exist_ok=True)
test.write_text("""package ir.rahyar.app.core.navigation

import ir.rahyar.app.domain.models.LatLng
import ir.rahyar.app.domain.models.Route
import ir.rahyar.app.domain.models.RouteType
import ir.rahyar.app.domain.models.TransportMode
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.LocalDateTime

class RoutePreviewSafetyTest {
    private fun route(
        id: String,
        type: RouteType = RouteType.ALTERNATIVE,
        duration: Int = 20,
        distance: Double = 10.0,
        points: List<LatLng> = listOf(LatLng(35.7, 51.4), LatLng(35.8, 51.5))
    ) = Route(
        id = id,
        type = type,
        points = points,
        durationMinutes = duration,
        distanceKm = distance,
        eta = LocalDateTime.now(),
        transportMode = TransportMode.CAR
    )

    @Test fun previewKeepsRecommendedPlusAtMostTwoAlternatives() {
        val selected = selectRoutePreviewRoutes(
            listOf(
                route("slow", duration = 40),
                route("recommended", RouteType.RECOMMENDED, duration = 30),
                route("fast", duration = 18),
                route("other", duration = 25)
            )
        )
        assertEquals(3, selected.size)
        assertEquals("recommended", selected.first().id)
        assertEquals(listOf("fast", "other"), selected.drop(1).map { it.id })
    }

    @Test fun malformedRoutesAreExcludedBeforeMapOrPreviewRendering() {
        val invalid = route("bad", distance = 0.0, points = listOf(LatLng(35.7, 51.4)))
        val valid = route("good", RouteType.RECOMMENDED)
        assertEquals(listOf("good"), selectRoutePreviewRoutes(listOf(invalid, valid)).map { it.id })
        assertFalse(isRenderableRoute(invalid))
        assertTrue(isRenderableRoute(valid))
    }

    @Test fun safeCameraPaddingReservesActualBottomOverlaySpace() {
        val idle = routePreviewCameraPadding(routeSheetVisible = false, stickyStartVisible = false)
        val sticky = routePreviewCameraPadding(routeSheetVisible = false, stickyStartVisible = true)
        val sheet = routePreviewCameraPadding(routeSheetVisible = true, stickyStartVisible = false)

        assertTrue(sticky.bottom > idle.bottom)
        assertTrue(sheet.bottom > sticky.bottom)
        assertEquals(150, sheet.top)
        assertEquals(28, sheet.start)
        assertEquals(28, sheet.end)
    }

    @Test fun sheetVisibilityDoesNotChangeCameraFitKey() {
        val routes = listOf(route("r", RouteType.RECOMMENDED))
        val before = routePreviewCameraFitKey(routes, 4)
        routePreviewCameraPadding(routeSheetVisible = false, stickyStartVisible = true)
        val after = routePreviewCameraFitKey(routes, 4)
        assertEquals(before, after)
    }

    @Test fun explicitOverviewRequestChangesCameraFitKey() {
        val routes = listOf(route("r", RouteType.RECOMMENDED))
        assertFalse(routePreviewCameraFitKey(routes, 4) == routePreviewCameraFitKey(routes, 5))
    }

    @Test fun stickyStartRequiresValidSelectedRouteAndNoBlockingOverlay() {
        val route = route("r", RouteType.RECOMMENDED)
        assertTrue(shouldShowStickyStart(route, blockingOverlayVisible = false))
        assertFalse(shouldShowStickyStart(route, blockingOverlayVisible = true))
        assertFalse(shouldShowStickyStart(null, blockingOverlayVisible = false))
    }

    @Test fun rapidDoubleStartIsRejectedButRetryDoesNotFreeze() {
        val gate = StartNavigationGate(1_200L)
        assertTrue(gate.tryAcquire(10_000L))
        assertFalse(gate.tryAcquire(10_100L))
        assertTrue(gate.tryAcquire(11_300L))
    }

    @Test fun resetAllowsImmediateRetryAfterSynchronousFailure() {
        val gate = StartNavigationGate(1_200L)
        assertTrue(gate.tryAcquire(10_000L))
        gate.reset()
        assertTrue(gate.tryAcquire(10_001L))
    }
}
""")

map_screen = root / "app/src/main/java/ir/rahyar/app/ui/screens/RahyarMapScreen.kt"
m = map_screen.read_text()

if "import android.os.SystemClock" not in m:
    m = m.replace("import android.graphics.PointF\\n", "import android.graphics.PointF\\nimport android.os.SystemClock\\n", 1)

core_imports = """import ir.rahyar.app.core.navigation.StartNavigationGate
import ir.rahyar.app.core.navigation.isRenderableRoute
import ir.rahyar.app.core.navigation.routePreviewCameraFitKey
import ir.rahyar.app.core.navigation.routePreviewCameraPadding
import ir.rahyar.app.core.navigation.selectRoutePreviewRoutes
import ir.rahyar.app.core.navigation.shouldShowStickyStart
"""
if "import ir.rahyar.app.core.navigation.StartNavigationGate" not in m:
    anchor = "import ir.rahyar.app.core.map.RahyarMapView\\n"
    if anchor not in m:
        raise SystemExit("Run51 core import anchor missing")
    m = m.replace(anchor, anchor + core_imports, 1)

if "import ir.rahyar.app.domain.models.CameraPadding" not in m:
    anchor = "import ir.rahyar.app.domain.models.LatLng\\n"
    if anchor not in m:
        raise SystemExit("Run51 CameraPadding import anchor missing")
    m = m.replace(anchor, "import ir.rahyar.app.domain.models.CameraPadding\\n" + anchor, 1)

m = m.replace(
    "val routeSheetState = rememberModalBottomSheetState(skipPartiallyExpanded = false)",
    "val routeSheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)",
    1
)

old_state = """    val success = routeState as? RoutePreviewUiState.Success
    val routes = success?.routes?.map { it.route }.orEmpty()
    val selectedRoute = success?.selectedRoute?.route
"""
new_state = """    val success = routeState as? RoutePreviewUiState.Success
    val routes = selectRoutePreviewRoutes(success?.routes?.map { it.route }.orEmpty())
    val selectedRoute = success?.selectedRoute?.route
        ?.takeIf(::isRenderableRoute)
        ?: routes.firstOrNull()
    val blockingOverlayVisible = showSearchSheet || showConfirmSheet || precisePickMode
    val stickyStartVisible = shouldShowStickyStart(selectedRoute, blockingOverlayVisible)
    val previewCameraPadding = routePreviewCameraPadding(
        routeSheetVisible = showRouteSheet,
        stickyStartVisible = stickyStartVisible
    )
    val startNavigationGate = remember { StartNavigationGate() }
"""
if old_state not in m:
    raise SystemExit("Run51 route state anchor missing")
m = m.replace(old_state, new_state, 1)

map_call_anchor = """            selectedRoute = selectedRoute,
            waypoints = session.waypoints,
            overviewRequestToken = overviewRequestToken,"""
map_call_replacement = """            selectedRoute = selectedRoute,
            waypoints = session.waypoints,
            overviewRequestToken = overviewRequestToken,
            cameraPadding = previewCameraPadding,"""
if map_call_anchor not in m:
    raise SystemExit("Run51 overview map call anchor missing")
m = m.replace(map_call_anchor, map_call_replacement, 1)

m = m.replace(
    "if (success != null && selectedRoute != null && !showSearchSheet && !showConfirmSheet && !precisePickMode) {",
    "if (success != null && selectedRoute != null && stickyStartVisible) {",
    1
)

old_start = """                onStartNavigation = { route ->
                    val selectedUi = success.routes.firstOrNull { it.route.id == route.id }
                    navigationSession.setTripContext(
                        weatherSummary = selectedUi?.weather?.summary,
                        trafficSummary = selectedUi?.traffic?.toTripTrafficSummary()
                    )
                    navigationSession.selectRoute(route)
                    showRouteSheet = false
                    onStartNavigation(route)
                }
"""
new_start = """                onStartNavigation = { route ->
                    if (startNavigationGate.tryAcquire(SystemClock.elapsedRealtime())) {
                        val selectedUi = success.routes.firstOrNull { it.route.id == route.id }
                        navigationSession.setTripContext(
                            weatherSummary = selectedUi?.weather?.summary,
                            trafficSummary = selectedUi?.traffic?.toTripTrafficSummary()
                        )
                        navigationSession.selectRoute(route)
                        showRouteSheet = false
                        runCatching { onStartNavigation(route) }
                            .onFailure { startNavigationGate.reset() }
                    }
                }
"""
if old_start not in m:
    raise SystemExit("Run51 sticky start callback anchor missing")
m = m.replace(old_start, new_start, 1)

old_sheet_start = """                    onStartNavigation = { route ->
                        val selectedUi = (routeState as? RoutePreviewUiState.Success)
                            ?.routes
                            ?.firstOrNull { it.route.id == route.id }

                        navigationSession.setTripContext(
                            weatherSummary = selectedUi?.weather?.summary,
                            trafficSummary = selectedUi?.traffic?.toTripTrafficSummary()
                        )
                        navigationSession.selectRoute(route)
                        showRouteSheet = false
                        onStartNavigation(route)
                    },"""
new_sheet_start = """                    onStartNavigation = { route ->
                        if (startNavigationGate.tryAcquire(SystemClock.elapsedRealtime())) {
                            val selectedUi = (routeState as? RoutePreviewUiState.Success)
                                ?.routes
                                ?.firstOrNull { it.route.id == route.id }

                            navigationSession.setTripContext(
                                weatherSummary = selectedUi?.weather?.summary,
                                trafficSummary = selectedUi?.traffic?.toTripTrafficSummary()
                            )
                            navigationSession.selectRoute(route)
                            showRouteSheet = false
                            runCatching { onStartNavigation(route) }
                                .onFailure { startNavigationGate.reset() }
                        }
                    },"""
if old_sheet_start not in m:
    raise SystemExit("Run51 route sheet start callback anchor missing")
m = m.replace(old_sheet_start, new_sheet_start, 1)

sig_old = """    waypoints: List<LatLng>,
    overviewRequestToken: Int,
    onLongPressDestination: (SearchResult) -> Unit,"""
sig_new = """    waypoints: List<LatLng>,
    overviewRequestToken: Int,
    cameraPadding: CameraPadding,
    onLongPressDestination: (SearchResult) -> Unit,"""
if sig_old not in m:
    raise SystemExit("Run51 RahyarOverviewMap signature anchor missing")
m = m.replace(sig_old, sig_new, 1)

old_route_ids = """    val routeIds = routes.take(3).joinToString("|") { it.id }
"""
new_route_ids = """    val routeIds = routes.take(3).joinToString("|") { it.id }
    val cameraFitKey = routePreviewCameraFitKey(routes, overviewRequestToken)
"""
if old_route_ids not in m:
    raise SystemExit("Run51 routeIds anchor missing")
m = m.replace(old_route_ids, new_route_ids, 1)

m = m.replace(
    "LaunchedEffect(mapRef, routeIds, overviewRequestToken) {",
    "LaunchedEffect(mapRef, cameraFitKey) {",
    1
)

old_padding = """                val density = context.resources.displayMetrics.density
                val horizontalPx = (28 * density).toInt()
                val topPx = (150 * density).toInt()
                val bottomPx = (220 * density).toInt()

                map.animateCamera(
                    CameraUpdateFactory.newLatLngBounds(
                        bounds,
                        horizontalPx,
                        topPx,
                        horizontalPx,
                        bottomPx
                    ),"""
new_padding = """                val density = context.resources.displayMetrics.density
                val startPx = (cameraPadding.start * density).toInt()
                val topPx = (cameraPadding.top * density).toInt()
                val endPx = (cameraPadding.end * density).toInt()
                val bottomPx = (cameraPadding.bottom * density).toInt()

                map.animateCamera(
                    CameraUpdateFactory.newLatLngBounds(
                        bounds,
                        startPx,
                        topPx,
                        endPx,
                        bottomPx
                    ),"""
if old_padding not in m:
    raise SystemExit("Run51 camera padding target missing")
m = m.replace(old_padding, new_padding, 1)

map_screen.write_text(m)

sheet = root / "app/src/main/java/ir/rahyar/app/ui/components/RoutePreviewSheet.kt"
s = sheet.read_text()

if "import ir.rahyar.app.core.navigation.isRenderableRoute" not in s:
    anchor = "import ir.rahyar.app.core.provider.ProviderManager\\n"
    if anchor not in s:
        raise SystemExit("Run51 RoutePreviewSheet import anchor missing")
    s = s.replace(
        anchor,
        anchor + "import ir.rahyar.app.core.navigation.isRenderableRoute\\nimport ir.rahyar.app.core.navigation.selectRoutePreviewRoutes\\n",
        1
    )

old_sheet_routes = """    val success = state as? RoutePreviewUiState.Success
    val routes = success?.routes?.map { it.route }.orEmpty()
    val primaryRoute = routes.firstOrNull { it.type == RouteType.RECOMMENDED }
        ?: routes.minByOrNull { it.durationMinutes }
    val alternatives = routes.filterNot { it.id == primaryRoute?.id }.take(2)
    val selectedUi = success?.selectedRoute
    val selectedRoute = selectedUi?.route
"""
new_sheet_routes = """    val success = state as? RoutePreviewUiState.Success
    val routes = selectRoutePreviewRoutes(success?.routes?.map { it.route }.orEmpty())
    val primaryRoute = routes.firstOrNull()
    val alternatives = routes.drop(1).take(2)
    val selectedUi = success?.selectedRoute
    val selectedRoute = selectedUi?.route
        ?.takeIf(::isRenderableRoute)
        ?: primaryRoute
"""
if old_sheet_routes not in s:
    raise SystemExit("Run51 RoutePreviewSheet route selection anchor missing")
s = s.replace(old_sheet_routes, new_sheet_routes, 1)
sheet.write_text(s)
