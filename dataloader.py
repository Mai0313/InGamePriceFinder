import sqlite3
import datetime

import pandas as pd
from pydantic import Field, BaseModel, ConfigDict, computed_field
from src.ingame_price import GameInfo

target_game = "原神"


class DataBaseManager(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    database_name: str = Field(...)

    @computed_field
    @property
    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_name)
        return conn

    @computed_field
    @property
    def table_names(self) -> list[str]:
        table_names_ = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table';", self.get_connection
        )
        table_names_ = table_names_["name"].values.tolist()
        return table_names_

    def save_table(self, data: pd.DataFrame) -> pd.DataFrame:
        data.to_sql(target_game, self.get_connection, index=False, if_exists="replace")
        return data

    def read_table(self, table_name: str) -> pd.DataFrame:
        if table_name in self.table_names:
            data = pd.read_sql_query(f"SELECT * FROM {table_name}", self.get_connection)
            return data
        else:
            raise ValueError(f"Table name {table_name} not found in the database")

    def update_country_currency(self) -> pd.DataFrame:
        country_currency = pd.read_csv("./data/currency_rates.csv")
        country_currency.to_sql(
            "currency_rates", self.get_connection, index=False, if_exists="replace"
        )
        return country_currency

    def update_ingame_price(self, table_name: str) -> pd.DataFrame:
        """這裡的table name可以是遊戲名稱 或是 任何名稱"""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if table_name in self.table_names:
            data = self.read_table(table_name)
            database_updated_date = data["database_updated_date"].values[0]
            # 如果資料在三天內就不更新
            if datetime.datetime.strptime(now, "%Y-%m-%d %H:%M:%S") - datetime.datetime.strptime(
                database_updated_date, "%Y-%m-%d %H:%M:%S"
            ) < datetime.timedelta(days=3):
                return data
            else:
                game_info_instance = GameInfo(target_game=target_game)
                country_currency = pd.read_csv("./data/currency_rates.csv")
                game_info_data = game_info_instance.fetch_data()
                game_info_data["database_updated_date"] = now
                self.save_table(game_info_data)
                return game_info_data
        else:
            game_info_instance = GameInfo(target_game=target_game)
            country_currency = pd.read_csv("./data/currency_rates.csv")
            game_info_data = game_info_instance.fetch_data()
            game_info_data["database_updated_date"] = now
            self.save_table(game_info_data)
            return game_info_data


if __name__ == "__main__":
    table_name = "原神"
    database_name = "./data/ingame_price.db"
    db_manager = DataBaseManager(database_name=database_name)
    data = db_manager.update_ingame_price(table_name=table_name)
    print(data)