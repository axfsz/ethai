import os
import pandas as pd
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from logging_config import logger

class DatabaseManager:
    """Manages all interactions with the InfluxDB time-series database."""

    def __init__(self, url: str, token: str, org: str, bucket: str):
        """Initializes the database connection using provided configuration."""
        self.influx_url = url
        self.influx_token = token
        self.influx_org = org
        self.bucket = bucket

        if not all([self.influx_url, self.influx_token, self.influx_org, self.bucket]):
            logger.error("InfluxDB configuration is incomplete. All parameters (URL, TOKEN, ORG, BUCKET) are required.")
            raise ValueError("InfluxDB configuration is incomplete.")

        self.client = InfluxDBClient(url=self.influx_url, token=self.influx_token, org=self.influx_org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
        logger.info(f"Successfully connected to InfluxDB at {self.influx_url}, org: '{self.influx_org}', bucket: '{self.bucket}'")

    def write_ohlcv_data(self, measurement: str, data: pd.DataFrame, symbol: str):
        """
        Writes OHLCV data from a pandas DataFrame to InfluxDB.

        Args:
            measurement (str): The measurement name (e.g., '1h', '5m').
            data (pd.DataFrame): DataFrame with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
            symbol (str): The trading symbol (e.g., 'ETH/USDT').
        """
        try:
            points = []
            for _, row in data.iterrows():
                point = (
                    Point(measurement)
                    .tag("symbol", symbol)
                    .field("open", row['open'])
                    .field("high", row['high'])
                    .field("low", row['low'])
                    .field("close", row['close'])
                    .field("volume", row['volume'])
                    .time(pd.to_datetime(row['timestamp'], unit='ms'))
                )
                points.append(point)
            
            self.write_api.write(bucket=self.bucket, org=self.influx_org, record=points)
            logger.info(f"Successfully wrote {len(points)} data points to measurement '{measurement}' for symbol {symbol}.")
        except Exception as e:
            logger.error(f"Failed to write data to InfluxDB: {e}")

    def query_ohlcv_data(self, measurement: str, symbol: str, time_range_start: str = "-7d") -> pd.DataFrame:
        """
        Queries OHLCV data from InfluxDB and returns it as a pandas DataFrame.

        Args:
            measurement (str): The measurement name (e.g., '1h', '5m').
            symbol (str): The trading symbol (e.g., 'ETH/USDT').
            time_range_start (str): The start of the time range for the query (e.g., '-1d', '-30d').

        Returns:
            pd.DataFrame: A DataFrame with the queried data, sorted by time.
        """
        try:
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {time_range_start})
              |> filter(fn: (r) => r._measurement == "{measurement}")
              |> filter(fn: (r) => r.symbol == "{symbol}")
              |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
              |> keep(columns: ["_time", "open", "high", "low", "close", "volume"])
              |> sort(columns: ["_time"])
            '''
            tables = self.query_api.query(query, org=self.influx_org)
            result_df = tables.to_pandas()
            if result_df.empty:
                logger.warning(f"Query for '{measurement}' on symbol {symbol} returned no data.")
                return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            # Convert time and set as index
            result_df.rename(columns={'_time': 'timestamp'}, inplace=True)
            result_df['timestamp'] = result_df['timestamp'].astype(int) // 10**6 # Convert to milliseconds
            result_df.set_index('timestamp', inplace=True)
            
            logger.info(f"Successfully queried {len(result_df)} data points from measurement '{measurement}' for symbol {symbol}.")
            return result_df.reset_index() # Return with timestamp as a column
        except Exception as e:
            logger.error(f"Failed to query data from InfluxDB: {e}")
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    def close(self):
        """Closes the InfluxDB client connection."""
        self.client.close()
        logger.info("InfluxDB client connection closed.")
