import pandas as pd
from typing import List, Tuple
from dataclasses import dataclass

# ================== 数据结构定义 ==================

@dataclass
class Kline:
    """标准K线数据结构"""
    time: any
    open: float
    high: float
    low: float
    close: float
    volume: float
    merged_high: float
    merged_low: float

@dataclass
class Fractal:
    """分型数据结构"""
    kline: Kline
    type: str  # 'top' 或 'bottom'

@dataclass
class Stroke:
    """笔数据结构"""
    start_fractal: Fractal
    end_fractal: Fractal
    direction: str  # 'up' 或 'down'
    high: float
    low: float

@dataclass
class Segment:
    """段数据结构"""
    strokes: List[Stroke]
    direction: str  # 'up' 或 'down'
    start_time: any
    end_time: any
    high: float
    low: float

@dataclass
class Center:
    """中枢数据结构"""
    segments: List[Segment]
    start_time: any
    end_time: any
    zg: float  # 中枢高点 (中枢区间上沿)
    zd: float  # 中枢低点 (中枢区间下沿)
    high: float # 中枢震荡的实际最高点
    low: float  # 中枢震荡的实际最低点

@dataclass
class BuySellPoint:
    """买卖点数据结构"""
    point_type: str  # e.g., '1st_buy', '1st_sell'
    time: any
    price: float
    segment: Segment # 触发该买卖点的段

# ================== 缠论分析引擎 ==================

class ChanAnalyzer:
    """缠论核心分析器，用于识别笔、段、中枢及买卖点"""

    def analyze(self, ohlcv: List[Tuple], macd_hist: List[float]) -> Tuple[List[Stroke], List[Segment], List[Center], List[BuySellPoint]]:
        """完整的缠论分析流程，输出所有结构"""
        strokes = self.find_strokes(ohlcv)
        segments = self.find_segments(strokes)
        centers = self.find_centers(segments)

        # 查找所有类型的买卖点
        first_points = self._find_first_buy_sell_points(segments, centers, macd_hist, ohlcv)
        second_points = self._find_second_buy_sell_points(segments, centers)
        third_points = self._find_third_buy_sell_points(segments, centers)

        all_points = first_points + second_points + third_points
        
        # 对买卖点进行去重和排序
        # 使用元组(time, type)作为key来确保唯一性
        unique_points_dict = { (p.time, p.point_type): p for p in all_points }
        buy_sell_points = sorted(list(unique_points_dict.values()), key=lambda p: p.time)

        return strokes, segments, centers, buy_sell_points

    def find_strokes(self, ohlcv: List[Tuple]) -> List[Stroke]:
        # ... (代码无变化)
        if not ohlcv or len(ohlcv) < 5: return []
        klines = self._merge_klines(ohlcv)
        fractals = self._find_fractals(klines)
        strokes = self._find_valid_strokes(fractals, klines)
        return strokes

    def find_segments(self, strokes: List[Stroke]) -> List[Segment]:
        # ... (代码无变化)
        segments = []
        if len(strokes) < 3: return segments
        current_segment_strokes = []
        for stroke in strokes:
            if not current_segment_strokes:
                current_segment_strokes.append(stroke)
                continue
            last_stroke_in_segment = current_segment_strokes[-1]
            if stroke.direction == last_stroke_in_segment.direction:
                if len(current_segment_strokes) >= 3:
                    seg_high = max(s.high for s in current_segment_strokes)
                    seg_low = min(s.low for s in current_segment_strokes)
                    segments.append(Segment(strokes=current_segment_strokes, direction=current_segment_strokes[0].direction, start_time=current_segment_strokes[0].start_fractal.kline.time, end_time=current_segment_strokes[-1].end_fractal.kline.time, high=seg_high, low=seg_low))
                current_segment_strokes = [stroke]
            else:
                current_segment_strokes.append(stroke)
        if len(current_segment_strokes) >= 3:
            seg_high = max(s.high for s in current_segment_strokes)
            seg_low = min(s.low for s in current_segment_strokes)
            segments.append(Segment(strokes=current_segment_strokes, direction=current_segment_strokes[0].direction, start_time=current_segment_strokes[0].start_fractal.kline.time, end_time=current_segment_strokes[-1].end_fractal.kline.time, high=seg_high, low=seg_low))
        return segments

    def find_centers(self, segments: List[Segment]) -> List[Center]:
        # ... (代码无变化)
        centers = []
        if len(segments) < 3: return centers
        for i in range(len(segments) - 2):
            s1, s2, s3 = segments[i], segments[i+1], segments[i+2]
            has_overlap = max(s1.low, s3.low) < min(s1.high, s3.high)
            if has_overlap:
                zd = max(s1.low, s3.low)
                zg = min(s1.high, s3.high)
                center_high = max(s1.high, s2.high, s3.high)
                center_low = min(s1.low, s2.low, s3.low)
                centers.append(Center(segments=[s1, s2, s3], start_time=s1.start_time, end_time=s3.end_time, zg=zg, zd=zd, high=center_high, low=center_low))
        return centers

    def _find_first_buy_sell_points(self, segments: List[Segment], centers: List[Center], macd_hist: List[float], ohlcv: List[Tuple]) -> List[BuySellPoint]:
        """步骤6：识别第一类买卖点（基于背驰）"""
        points = []
        if not centers or len(segments) < 2:
            return points

        # 找到最后一个中枢
        last_center = centers[-1]
        
        # 找到离开中枢的最后一段
        leaving_segment_index = segments.index(last_center.segments[-1]) + 1
        if leaving_segment_index >= len(segments):
            return points # 没有离开段
        leaving_segment = segments[leaving_segment_index]

        # 找到进入中枢的那一段
        entering_segment = last_center.segments[0]

        # 必须是同向的段才能比较力度
        if leaving_segment.direction != entering_segment.direction:
            return points

        # 计算两段的MACD面积以判断背驰
        kline_times = [k[0] for k in ohlcv]
        entering_area = self._calculate_macd_area(entering_segment, macd_hist, kline_times)
        leaving_area = self._calculate_macd_area(leaving_segment, macd_hist, kline_times)

        # 判断下跌趋势中的盘整背驰（一类买点）
        if leaving_segment.direction == 'down' and leaving_segment.low < entering_segment.low:
            if abs(leaving_area) < abs(entering_area): # MACD底背离
                points.append(BuySellPoint(
                    point_type='1st_buy',
                    time=leaving_segment.end_time,
                    price=leaving_segment.low,
                    segment=leaving_segment
                ))

        # 判断上涨趋势中的盘整背驰（一类卖点）
        if leaving_segment.direction == 'up' and leaving_segment.high > entering_segment.high:
            if abs(leaving_area) < abs(entering_area): # MACD顶背离
                points.append(BuySellPoint(
                    point_type='1st_sell',
                    time=leaving_segment.end_time,
                    price=leaving_segment.high,
                    segment=leaving_segment
                ))

        return points

    def _calculate_macd_area(self, segment: Segment, macd_hist: List[float], kline_times: List[any]) -> float:
        """计算一个段对应的MACD柱状图面积"""
        try:
            start_index = kline_times.index(segment.start_time)
            end_index = kline_times.index(segment.end_time)
            return sum(macd_hist[start_index : end_index + 1])
        except (ValueError, IndexError):
            return 0.0

    def _find_second_buy_sell_points(self, segments: List[Segment], centers: List[Center]) -> List[BuySellPoint]:
        """步骤7：识别第二类买卖点。
        
        第二类买卖点发生在中枢之后，是回调/反弹不创新低/新高的点。
        - 二类买点：离开中枢的向上段后的回调段，其低点高于中枢的低点(zd)。
        - 二类卖点：离开中枢的向下段后的反弹段，其高点低于中枢的高点(zg)。
        """
        points = []
        if not centers:
            return points

        for center in centers:
            try:
                # 找到中枢后的第一个和第二个段
                last_center_segment_index = segments.index(center.segments[-1])
                segments_after_center = segments[last_center_segment_index + 1:]
            except (ValueError, IndexError):
                continue

            if len(segments_after_center) < 2:
                continue

            s1 = segments_after_center[0]
            s2 = segments_after_center[1]

            # 检查第二类买点 (上升趋势中枢后)
            if s1.direction == 'up' and s2.direction == 'down':
                if s2.low > center.zd:
                    points.append(BuySellPoint(
                        point_type='2nd_buy',
                        time=s2.end_time,
                        price=s2.low,
                        segment=s2
                    ))

            # 检查第二类卖点 (下降趋势中枢后)
            if s1.direction == 'down' and s2.direction == 'up':
                if s2.high < center.zg:
                    points.append(BuySellPoint(
                        point_type='2nd_sell',
                        time=s2.end_time,
                        price=s2.high,
                        segment=s2
                    ))
        return points

    def _find_third_buy_sell_points(self, segments: List[Segment], centers: List[Center]) -> List[BuySellPoint]:
        """步骤8：识别第三类买卖点。
        
        第三类买卖点确认中枢的结束和新趋势的开始。
        - 三类买点：离开中枢的向上段后的回调段，其低点高于中枢的高点(zg)。
        - 三类卖点：离开中枢的向下段后的反弹段，其高点低于中枢的低点(zd)。
        """
        points = []
        if not centers:
            return points
        
        for center in centers:
            try:
                last_center_segment_index = segments.index(center.segments[-1])
                segments_after_center = segments[last_center_segment_index + 1:]
            except (ValueError, IndexError):
                continue

            if len(segments_after_center) < 2:
                continue

            s1 = segments_after_center[0]
            s2 = segments_after_center[1]

            # 检查第三类买点 (确认上升趋势)
            if s1.direction == 'up' and s2.direction == 'down':
                if s2.low > center.zg:
                    points.append(BuySellPoint(
                        point_type='3rd_buy',
                        time=s2.end_time,
                        price=s2.low,
                        segment=s2
                    ))

            # 检查第三类卖点 (确认下降趋势)
            if s1.direction == 'down' and s2.direction == 'up':
                if s2.high < center.zd:
                    points.append(BuySellPoint(
                        point_type='3rd_sell',
                        time=s2.end_time,
                        price=s2.high,
                        segment=s2
                    ))
        return points

    def _merge_klines(self, ohlcv: List[Tuple]) -> List[Kline]:
        """处理K线包含关系"""
        klines = [Kline(time=row[0], open=row[1], high=row[2], low=row[3], close=row[4], volume=row[5], merged_high=row[2], merged_low=row[3]) for row in ohlcv]
        i = 1
        while i < len(klines):
            prev_k, curr_k = klines[i-1], klines[i]
            is_contained = prev_k.merged_high >= curr_k.merged_high and prev_k.merged_low <= curr_k.merged_low
            is_containing = curr_k.merged_high >= prev_k.merged_high and curr_k.merged_low <= prev_k.merged_low
            if is_contained or is_containing:
                merged_high = max(prev_k.merged_high, curr_k.merged_high)
                merged_low = max(prev_k.merged_low, curr_k.merged_low)
                klines[i-1].merged_high, klines[i-1].merged_low = merged_high, merged_low
                klines.pop(i)
                i = 1
            else:
                i += 1
        return klines

    def _find_fractals(self, klines: List[Kline]) -> List[Fractal]:
        """从合并后的K线中找到所有分型"""
        fractals = []
        for i in range(1, len(klines) - 1):
            prev_k, curr_k, next_k = klines[i-1], klines[i], klines[i+1]
            if curr_k.merged_high > prev_k.merged_high and curr_k.merged_high > next_k.merged_high:
                fractals.append(Fractal(kline=curr_k, type='top'))
            if curr_k.merged_low < prev_k.merged_low and curr_k.merged_low < next_k.merged_low:
                fractals.append(Fractal(kline=curr_k, type='bottom'))
        return fractals

    def _find_valid_strokes(self, fractals: List[Fractal], klines: List[Kline]) -> List[Stroke]:
        """连接分型，形成有效的笔"""
        strokes = []
        if len(fractals) < 2:
            return strokes
        last_fractal = None
        for curr_fractal in fractals:
            if last_fractal is None:
                last_fractal = curr_fractal
                continue
            if curr_fractal.type == last_fractal.type:
                if curr_fractal.type == 'top' and curr_fractal.kline.merged_high > last_fractal.kline.merged_high:
                    last_fractal = curr_fractal
                elif curr_fractal.type == 'bottom' and curr_fractal.kline.merged_low < last_fractal.kline.merged_low:
                    last_fractal = curr_fractal
                continue
            
            start_k_index = klines.index(last_fractal.kline)
            end_k_index = klines.index(curr_fractal.kline)
            if abs(end_k_index - start_k_index) > 1:
                direction = 'down' if curr_fractal.type == 'bottom' else 'up'
                stroke = Stroke(
                    start_fractal=last_fractal, end_fractal=curr_fractal, direction=direction,
                    high=max(last_fractal.kline.merged_high, curr_fractal.kline.merged_high),
                    low=min(last_fractal.kline.merged_low, curr_fractal.kline.merged_low)
                )
                strokes.append(stroke)
                last_fractal = curr_fractal
        return strokes

