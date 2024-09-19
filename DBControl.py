from sqlite3 import connect


class DataBase:
    def __init__(self, db_path):
        self.connection = connect(db_path, timeout=10)
        self.cursor = self.connection.cursor()

    def check_user_data(self, user_tg):
        result = self.cursor.execute(
            f"SELECT count(*) FROM Users WHERE Telegram == {user_tg} "
            f"AND FirstName IS NOT NULL AND Surname IS NOT NULL AND Address IS NOT NULL")
        if result.fetchone()[0] == 1:
            return True
        return False

    def check_user_registration(self, user_tg):
        result = self.cursor.execute(
            f"SELECT count(*) FROM Users WHERE Telegram == {user_tg} "
            f"AND FirstName IS NOT NULL AND Surname IS NOT NULL")
        if result.fetchone()[0] == 1:
            return True
        return False

    def delete_user(self, user_tg):
        self.cursor.execute(
            f"DELETE FROM Users WHERE Telegram = {user_tg}")
        self.connection.commit()

    def get_user_info(self, user_tg):
        result = self.cursor.execute(
            f"SELECT FirstName, Surname, Patronymic, Address FROM Users WHERE Telegram = '{user_tg}'").fetchone()
        return {"user": {"FirstName": result[0], "Surname": result[1], "Patronymic": result[2]}, "Address": result[3]}

    def check_user_address(self, user_tg):
        result = self.cursor.execute(
            f"SELECT count(*) FROM Users WHERE Telegram == {user_tg} AND Address IS NOT NULL")
        if result.fetchone()[0] == 1:
            return True
        return False

    def new_user(self, user_tg, first_name=None, surname=None, patronymic=None, address=None):
        if not (first_name or surname or patronymic or address):
            return -1
        fields, values = ["Telegram"], [str(user_tg)]
        for i in [(first_name, "FirstName"), (surname, "Surname"), (patronymic, "Patronymic"), (address, "Address")]:
            if not i[0] is None:
                values.append(f"'{i[0]}'")
                fields.append(i[1])
        self.cursor.execute(f'INSERT INTO Users({", ".join(fields)}) VALUES ({", ".join(values)})')
        self.connection.commit()

    def add_user_info(self, user_tg, first_name=None, surname=None, patronymic=None, address=None):
        if not (first_name or surname or patronymic or address):
            return -1
        request = "UPDATE Users SET "
        for i in [(first_name, "FirstName"), (surname, "Surname"), (patronymic, "Patronymic"), (address, "Address")]:
            if not i[0] is None:
                request += f"{i[1]} = '{i[0]}',"
        request = request[:-1]
        request += f" WHERE Telegram = {user_tg}"
        self.cursor.execute(request)
        self.connection.commit()

    def get_price_list(self):
        result = self.cursor.execute("SELECT * FROM PriceList")
        return result.fetchall()

    def new_request(self, user_tg, services: list, details=""):
        if not services:
            return -1
        self.cursor.execute(
            f'INSERT INTO Requests(User_ID, Details, Complete) VALUES ((SELECT User_ID FROM Users WHERE Telegram = \
            {user_tg}), "{details}", 0)')
        request_id = self.cursor.execute("SELECT last_insert_rowid()").fetchone()[0]
        request = f"INSERT INTO Services (Request_ID, Price_ID) VALUES" \
                  f" {', '.join([f'({request_id}, {services[i]})' for i in range(len(services))])}"
        self.cursor.execute(request)
        self.connection.commit()
        return request_id

    def get_user_by_request(self, request_id):
        result = self.cursor.execute(f"SELECT Users.Telegram FROM Users JOIN Requests on Users.User_ID"
                                     f" = Requests.User_ID WHERE Request_ID = {request_id}")
        return result.fetchone()[0]

    def get_request(self, request_id):
        result = self.cursor.execute(f"SELECT \
            Requests.Team_ID as team,\
            Requests.UNIX as unix,\
            Requests.Details as details,\
            Requests.Complete as complete,\
            PriceList.Name as service,\
            PriceList.Price as price,\
            PriceList.Description as description\
            FROM Requests\
            JOIN Services ON Requests.Request_ID = Services.Request_ID\
            JOIN PriceList ON PriceList.Price_ID= Services.Price_ID \
            WHERE Requests.Request_ID = {request_id}").fetchall()
        return {
            "team": result[0][0],
            "time": result[0][1],
            "details": result[0][2],
            "complete": result[0][3],
            "service": [(i[4], i[5], i[6]) for i in result]
        }

    def get_team_requests(self, team_tg):
        result = self.cursor.execute(f"SELECT \
            Requests.Request_ID,\
            Requests.UNIX,\
            Users.FirstName,\
            Users.Surname,\
            Users.Patronymic,\
            Users.Address,\
            Requests.Details\
            FROM Requests \
            JOIN Users on Users.User_ID = Requests.User_ID\
            WHERE Requests.Team_ID = (SELECT Team_ID FROM Teams WHERE Telegram = {team_tg}) AND Requests.Complete = 0\
            ORDER BY Requests.UNIX")

        tasks = []
        for a in result.fetchall():
            tasks.append(
                {"request_id": a[0], "time": a[1], "user": {"FirstName": a[2], "Surname": a[3], "Patronymic": a[4]},
                 "Address": a[5], "Details": a[6], })
        return tasks

    def set_request_complete(self, request_id):
        self.cursor.execute(f"UPDATE Requests SET Complete = 1 Where Request_ID = {request_id}")
        self.connection.commit()

    def get_user_requests(self, user_tg):
        result = self.cursor.execute(f"SELECT Request_ID, Details FROM Requests WHERE User_ID = "
                                     f"(SELECT User_ID FROM Users WHERE Telegram = {user_tg}) "
                                     f"AND Complete = 0").fetchall()
        return result

    def set_team_to_request(self, team_tg, request_id, time):
        self.cursor.execute(
            f"UPDATE Requests SET Team_ID = (SELECT Team_ID FROM Teams WHERE Telegram = {team_tg}), UNIX = {time} Where Request_ID = {request_id}")
        self.connection.commit()

    def get_teams(self):
        return self.cursor.execute("SELECT Team_ID, Telegram FROM Teams").fetchall()

    def get_free_requests(self):
        result = self.cursor.execute(f"SELECT \
            Requests.Request_ID,\
            Requests.UNIX,\
            Users.FirstName,\
            Users.Surname,\
            Users.Patronymic,\
            Users.Address,\
            Requests.Details\
            FROM Requests \
            JOIN Users on Users.User_ID = Requests.User_ID\
            WHERE (Requests.UNIX is NULL or Requests.Team_ID is NULL) AND Requests.Complete = 0")
        tasks = []
        for a in result.fetchall():
            tasks.append(
                {"request_id": a[0], "time": a[1], "user": {"FirstName": a[2], "Surname": a[3], "Patronymic": a[4]},
                 "Address": a[5], "Details": a[6], })
        return tasks