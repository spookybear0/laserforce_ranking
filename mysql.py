# made by realistikdash
from typing import Union, Tuple
import aiomysql
import asyncio
import os

import pymysql
from config import config  # type: ignore


class MySQLPool:
    """The wrapper around the `aiomysql` module. It allows for
    the simple usage of the database within many circumstances while
    respecting the one connection at a time rule.

    Creating a wrapper as such allows us to quickly change the module used for
    MySQL without rewriting a large portion of the codebase.
    Classmethods:
        connect: Creates a connection to the MySQL server and establishes a
            pool.
    """

    def __init__(self):
        """Creates the default values for the connector. Use the `conntect`
        classmethod instead."""
        self._pool: aiomysql.Pool = None
        self.last_row_id: int = 0
        self._loop: asyncio.AbstractEventLoop

    @classmethod
    async def connect(
        cls,
        host: str,
        user: str,
        password: str,
        database: str,
        port: int = 3306,
        loop: asyncio.AbstractEventLoop = None,
    ):
        """Creates the MySQL connecton pool. Handles authentication and the
        configuration of the object.

        Note:
            Calling this function allows for the usage of all functions within
                this class, such as `fetchone`.

        Args:
            host (str): The hostname of the MySQL server you would like to
                connect. Usually `localhost`.
            user (str): The username of the MySQL user you would like to log
                into.
            password (str): The password of the MySQL user you would like to
                log into.
            database (str): The database you would like to interact with.
            port (int): The port at which the MySQL server is located at.
                Default set to 3306.
            loop (AbstractEventLoop): The event loop that should be used
                for the MySQL pool. If not set or equal to None, a new
                one will be created.
        """

        cls = cls()

        await cls.connect_local(
            host,
            user,
            password,
            database,
            port,
            asyncio.get_event_loop() if loop is None else loop,
        )

        return cls

    async def connect_local(
        self,
        host: str,
        user: str,
        password: str,
        database: str,
        port: int = 3306,
        loop: asyncio.AbstractEventLoop = None,
    ):
        """Connects the current object to the pool without creating a new
        object.

        Args:
            host (str): The hostname of the MySQL server you would like to
                connect. Usually `localhost`.
            user (str): The username of the MySQL user you would like to log
                into.
            password (str): The password of the MySQL user you would like to
                log into.
            database (str): The database you would like to interact with.
            port (int): The port at which the MySQL server is located at.
                Default set to 3306.
            loop (AbstractEventLoop): The event loop that should be used
                for the MySQL pool.
        """

        self._pool = await aiomysql.create_pool(
            host=host, port=port, user=user, password=password, db=database, loop=loop
        )

    async def fetchone(self, query: str, args: tuple = ()) -> Union[tuple, None]:
        """Executes `query` in MySQL and returns the first result.

        Args:
            query (str): The MySQL query to be executed.
            args (tuple, list): The list or tuple of arguments to be safely
                formatted into the query.

        Returns:
            Tuple in the arrangement specified within the query if a result is
                found.
            None if no results are found.
        """
        if not self._pool:
            if os.name == "nt":
                loop = asyncio.get_event_loop()
            else:
                import uvloop

                loop = uvloop.new_event_loop()

            await self.connect_local(
                config["db_host"],
                config["db_user"],
                config["db_password"],
                config["db_database"],
                config["db_port"],
                loop,
            )
        # Fetch a connection from the pool.
        async with self._pool.acquire() as pool:
            # Grab a cur.
            async with pool.cursor() as cur:
                # Execute and fetchone.
                async def execute():
                    try:
                        await cur.execute(query, args)
                    except pymysql.InternalError:
                        await execute()

                await execute()

                # Immidiately return it
                return await cur.fetchone()

    async def fetchall(self, query: str, args: tuple = ()) -> Tuple[tuple]:
        """Executes `query` in MySQL and returns all of the found results.

        Args:
            query (str): The MySQL query to be executed.
            args (tuple, list): The list or tuple of arguments to be safely
                formatted into the query.

        Returns:
            Tuple of tuples with the results found.

        """
        if not self._pool:
            if os.name == "nt":
                loop = asyncio.get_event_loop()
            else:
                import uvloop

                loop = uvloop.new_event_loop()

            await self.connect_local(
                config["db_host"],
                config["db_user"],
                config["db_password"],
                config["db_database"],
                config["db_port"],
                loop,
            )

        # Fetch a connection from the pool.
        async with self._pool.acquire() as pool:
            # Grab a cur.
            async with pool.cursor() as cur:
                # Execute and fetchall.
                async def execute():
                    try:
                        await cur.execute(query, args)
                    except pymysql.InternalError:
                        await execute()

                await execute()

                # Immidiately return it
                return await cur.fetchall()

    async def execute(self, query: str, args: tuple = ()) -> int:
        """Simply executes `query` and commits all changes made by it to
        database.

        Note:
            Please don't use this function for select queries. For them rather
                use `fetchall` and `fetchone`

        Args:
            query (str): The MySQL query to be executed.
            args (tuple, list): The list or tuple of arguments to be safely
                formatted into the query.

        Returns:
            The ID of the last row affected.
        """
        if not self._pool:
            if os.name == "nt":
                loop = asyncio.get_event_loop()
            else:
                import uvloop

                loop = uvloop.new_event_loop()

            await self.connect_local(
                config["db_host"],
                config["db_user"],
                config["db_password"],
                config["db_database"],
                config["db_port"],
                loop,
            )
        # Fetch a connection from the pool.
        async with self._pool.acquire() as pool:
            # Grab a cur.
            async with pool.cursor() as cur:
                # Execute it.
                async def execute():
                    try:
                        await cur.execute(query, args)
                    except pymysql.InternalError:
                        await execute()

                await execute()

                # Set `last_row_id`
                self.last_row_id = cur.lastrowid

                # Commit it.
                await pool.commit()

                # Return it
                return cur.lastrowid
