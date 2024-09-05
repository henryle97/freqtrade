import talib.abstract as ta
from pandas import DataFrame
from technical import qtpylib

from freqtrade.strategy import IStrategy


class SonicRStrategy(IStrategy):
    """
    SonicR strategy
    - Main timeframe: 4h
    - Context:
        + EMA34 > EMA89
        + 50 < RSI14 < 60
    - Signal:
        + Bullish candlestick pattern
        + Lowest price near ema34, close price > ema34
    """

    INTERFACE_VERSION = 3

    can_short: bool = False

    timeframe = "4h"

    startup_candle_count: int = 200

    stoploss = -0.05

    def informative_pairs(self):
        return []

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # EMA
        dataframe["ema34"] = ta.EMA(dataframe, timeperiod=34)
        dataframe["ema89"] = ta.EMA(dataframe, timeperiod=89)

        # RSI
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)

        # pattern recognition - bullish candlestick
        ## hammer pattern
        # dataframe["CDLHAMMER"] = ta.CDLHAMMER(dataframe)
        ## Inverted hammer pattern
        dataframe["CDLINVERTEDHAMMER"] = ta.CDLINVERTEDHAMMER(dataframe)
        ## Bullish engulfing pattern
        # dataframe["CDLENGULFING"] = ta.CDLENGULFING(dataframe)
        ## doji
        dataframe["CDLDOJI"] = ta.CDLDOJI(dataframe)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # ema34 > ema89
        dataframe.loc[(dataframe["ema34"] >= dataframe["ema89"]), "ema_trend"] = "up"
        dataframe.loc[(dataframe["ema34"] < dataframe["ema89"]), "ema_trend"] = "down"
        # 50 < rsi < 60
        dataframe.loc[(dataframe["rsi"] > 50) & (dataframe["rsi"] < 60), "rsi_trend"] = "up"
        dataframe.loc[(dataframe["rsi"] <= 50) | (dataframe["rsi"] >= 60), "rsi_trend"] = "down"

        # close price > open price
        dataframe.loc[(dataframe["close"] > dataframe["open"]), "price_high_trend"] = "up"

        # Lowest price below ema34, close price > ema34
        # dataframe.loc[
        #     (qtpylib.crossed_below(dataframe["low"], dataframe["ema34"]))
        #     & (dataframe["close"] > dataframe["ema34"]),
        #     "price_trend",
        # ] = "up"

        # close price above ema34
        dataframe.loc[(dataframe["close"] > dataframe["ema34"]), "price_trend"] = "up"

        # Bullish candlestick pattern
        dataframe.loc[
            (dataframe["CDLDOJI"] > 0) | (dataframe["CDLINVERTEDHAMMER"] > 0),
            # | (dataframe["CDLENGULFING"] > 0),
            "candle_trend",
        ] = "up"

        # combine all trend -> signal
        dataframe.loc[
            (dataframe["ema_trend"] == "up")
            # & (dataframe["rsi_trend"] == "up")
            & (dataframe["price_trend"] == "up")
            & (dataframe["price_high_trend"] == "up")
            & (dataframe["candle_trend"] == "up"),
            "enter_long",
        ] = 1

        # notify signal if previsous candle have enter_long = 1
        if dataframe["enter_long"].iloc[-1] == 1:
            self.dp.send_msg(
                f"Signal: Enter Long for {metadata['pair']} with previous close price {dataframe['close'].iloc[-1]}"
            )
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[
            (
                # RSI crosse above 80
                (qtpylib.crossed_above(dataframe["rsi"], 80)) & (dataframe["ema_trend"] == "down")
            ),
            "exit_long",
        ] = 1
        return dataframe
