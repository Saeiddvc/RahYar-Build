package ir.rahyar.app.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import ir.rahyar.app.core.navigation.TripStoryEffectKind
import ir.rahyar.app.core.navigation.TripStoryRuntimeData
import ir.rahyar.app.core.navigation.TripStoryViewMode
import ir.rahyar.app.core.navigation.tripStoryEffectsAt
import ir.rahyar.app.core.navigation.tripStoryMotionFrame
import ir.rahyar.app.core.navigation.tripStoryVisibleTrace
import kotlinx.coroutines.delay

@Composable
fun TripStoryMotionView(
    story: TripStoryRuntimeData,
    modifier: Modifier = Modifier
) {
    var mode by remember { mutableStateOf(TripStoryViewMode.DRIVER) }
    var progress by remember(story.tripId) { mutableFloatStateOf(0f) }

    LaunchedEffect(story.tripId, mode) {
        progress = 0f
        while (progress < 1f) {
            delay(55L)
            progress = (progress + 0.01f).coerceAtMost(1f)
        }
    }

    val frame = tripStoryMotionFrame(story, mode, progress)
    val visible = tripStoryVisibleTrace(story, mode, progress)
    val effects = frame?.let { tripStoryEffectsAt(story, it.timestampMillis) }.orEmpty()
    val routeColor = MaterialTheme.colorScheme.primary
    val markerColor = MaterialTheme.colorScheme.tertiary
    val panelColor = MaterialTheme.colorScheme.surfaceVariant

    Column(modifier) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            TripStoryViewMode.values().forEach { item ->
                FilterChip(
                    selected = mode == item,
                    onClick = { mode = item },
                    label = {
                        Text(
                            when (item) {
                                TripStoryViewMode.DRIVER -> "راننده"
                                TripStoryViewMode.AERIAL -> "هوایی"
                                TripStoryViewMode.OVERVIEW -> "نمای کلی"
                            }
                        )
                    }
                )
            }
        }

        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 8.dp),
            shape = RoundedCornerShape(18.dp),
            color = panelColor
        ) {
            Canvas(
                Modifier
                    .fillMaxWidth()
                    .height(190.dp)
                    .background(panelColor)
                    .padding(12.dp)
            ) {
                if (visible.size < 2) return@Canvas
                val minLat = visible.minOf { it.latitude }
                val maxLat = visible.maxOf { it.latitude }
                val minLon = visible.minOf { it.longitude }
                val maxLon = visible.maxOf { it.longitude }
                val latSpan = (maxLat - minLat).coerceAtLeast(0.000001)
                val lonSpan = (maxLon - minLon).coerceAtLeast(0.000001)
                val pad = 12f

                fun mapPoint(index: Int): Offset {
                    val point = visible[index]
                    val x = pad +
                        ((point.longitude - minLon) / lonSpan).toFloat() *
                        (size.width - pad * 2)
                    val y = size.height - pad -
                        ((point.latitude - minLat) / latSpan).toFloat() *
                        (size.height - pad * 2)
                    return Offset(x, y)
                }

                val path = Path()
                val first = mapPoint(0)
                path.moveTo(first.x, first.y)
                for (i in 1 until visible.size) {
                    val p = mapPoint(i)
                    path.lineTo(p.x, p.y)
                }
                drawPath(
                    path = path,
                    color = routeColor,
                    style = Stroke(
                        width = when (mode) {
                            TripStoryViewMode.DRIVER -> 8f
                            TripStoryViewMode.AERIAL -> 6f
                            TripStoryViewMode.OVERVIEW -> 4f
                        },
                        cap = StrokeCap.Round
                    )
                )
                drawCircle(
                    color = markerColor,
                    radius = 8f,
                    center = mapPoint(visible.lastIndex)
                )
            }
        }

        if (effects.isNotEmpty()) {
            Row(
                Modifier
                    .fillMaxWidth()
                    .padding(top = 6.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                effects.forEach { effect ->
                    Text(
                        text = when (effect) {
                            TripStoryEffectKind.RAIN -> "باران واقعی"
                            TripStoryEffectKind.SNOW -> "برف واقعی"
                            TripStoryEffectKind.FOG -> "مه واقعی"
                            TripStoryEffectKind.HEAVY_TRAFFIC -> "ترافیک سنگین واقعی"
                            TripStoryEffectKind.MEDIA_MOMENT -> "لحظه رسانه‌ای واقعی"
                        },
                        style = MaterialTheme.typography.labelSmall
                    )
                }
            }
        }
    }
}
