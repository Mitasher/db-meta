#!/bin/sh
# Пользователь SQL-консоли: читать и менять строки можно, менять схему и раздавать права — нет.
# Выполняется MySQL при первом запуске на пустом volume; на уже заполненной базе — вручную (шаг 4).
mysql -uroot -p"$MYSQL_ROOT_PASSWORD" <<SQL
CREATE USER IF NOT EXISTS '$SOURCE_DB_CONSOLE_USER'@'%' IDENTIFIED BY '$SOURCE_DB_CONSOLE_PASSWORD';
ALTER USER '$SOURCE_DB_CONSOLE_USER'@'%' IDENTIFIED BY '$SOURCE_DB_CONSOLE_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE ON \`$MYSQL_DATABASE\`.* TO '$SOURCE_DB_CONSOLE_USER'@'%';
SQL
