"""Генератор тестовых данных кастинга для source-db (MySQL)."""

import argparse
import datetime
import gzip
import io
import random
from pathlib import Path


def read_lines(data_dir: Path, file_name: str) -> list[str]:
    """Читает непустые строки исходного файла."""
    with open(data_dir / file_name, "r", encoding="utf-8") as file:
        lines = [line.strip() for line in file]
    return [line for line in lines if line != ""]


def random_date(rng: random.Random) -> datetime.date:
    """Случайная дата рождения с 1960 по 2005 год."""
    start = datetime.date(1960, 1, 1)
    end = datetime.date(2005, 12, 31)
    return start + datetime.timedelta(days=rng.randint(0, (end - start).days))


def random_passport(rng: random.Random) -> str:
    """Номер паспорта вида «1234 567890»."""
    series = "".join(rng.choices("0123456789", k=4))
    number = "".join(rng.choices("0123456789", k=6))
    return f"{series} {number}"


def passing_label(passed: bool) -> str:
    """Подпись результата этапа для колонки passing."""
    if passed:
        return "Этап пройден"
    return "Этап не пройден"


def pick_with_limit(rng: random.Random, load: dict[int, int], limit: int) -> int:
    """Выбирает id, у которого ещё не набран лимит фильмов."""
    candidates = [person_id for person_id, count in load.items() if count < limit]
    if len(candidates) == 0:
        raise ValueError("Не хватает людей, чтобы распределить фильмы с заданным лимитом")
    person_id = rng.choice(candidates)
    load[person_id] += 1
    return person_id


def make_role_types() -> list[dict]:
    """Справочник типов ролей."""
    names = ["Главная", "Второстепенная", "Эпизодическая"]
    return [{"id_role_type": index + 1, "name": name} for index, name in enumerate(names)]


def make_genres() -> list[dict]:
    """Справочник жанров."""
    names = [
        "Боевик", "Байопик", "Детектив", "Военный", "Вестерн", "Документальный", "Исторический",
        "Комедия", "Драма", "Криминал", "Мюзикл", "Мелодрама", "Приключения", "Фантастика",
        "Фентези", "Триллер", "Ужасы", "Нуар", "Спорт", "Научный",
    ]
    return [{"id_genres": index + 1, "name": name} for index, name in enumerate(names)]


def make_film_people(rng: random.Random, lines: list[str], count: int, id_column: str) -> list[dict]:
    """Режиссёры или кастинг-директора из строк «Имя Фамилия»."""
    if len(lines) < count:
        raise ValueError(f"В файле {len(lines)} строк, а нужно {count}")
    shuffled = list(lines)
    rng.shuffle(shuffled)
    rows = []
    for index in range(count):
        parts = shuffled[index].split(maxsplit=1)
        rows.append({
            id_column: index + 1,
            "surname": parts[1] if len(parts) == 2 else None,
            "name": parts[0],
            "patronymic": None,
            "date_of_birth": random_date(rng),
            "passport_number": random_passport(rng),
            "filmography": None,
        })
    return rows


def make_actors(
    rng: random.Random,
    count: int,
    full_names: list[str],
    educations: list[str],
    universities: list[str],
    works: list[str],
) -> list[dict]:
    """Актёры: ФИО, образование, опыт работы."""
    rows = []
    for actor_id in range(1, count + 1):
        full_name = rng.choice(full_names)
        parts = full_name.split()
        if len(parts) != 3:
            raise ValueError(f"Ожидалось «Фамилия Имя Отчество», а в файле: {full_name}")
        education = rng.choice(educations)
        if education == "Высшее образование":
            education = f"{education} {rng.choice(universities)}"
        rows.append({
            "id_actor": actor_id,
            "surname": parts[0],
            "name": parts[1],
            "patronymic": parts[2],
            "date_of_birth": random_date(rng),
            "passport_number": random_passport(rng),
            "education": education,
            "work_experience": rng.choice(works),
        })
    return rows


def make_films(
    rng: random.Random,
    titles: list[str],
    count: int,
    director_ids: list[int],
    casting_director_ids: list[int],
    max_films_per_person: int,
) -> list[dict]:
    """Фильмы с режиссёром и кастинг-директором."""
    if len(titles) < count:
        raise ValueError(f"В films.txt {len(titles)} названий, а нужно {count}")
    shuffled = list(titles)
    rng.shuffle(shuffled)
    director_load = {director_id: 0 for director_id in director_ids}
    casting_load = {casting_id: 0 for casting_id in casting_director_ids}
    rows = []
    for index in range(count):
        rows.append({
            "id_film": index + 1,
            "name": shuffled[index],
            "id_director": pick_with_limit(rng, director_load, max_films_per_person),
            "id_casting_director": pick_with_limit(rng, casting_load, max_films_per_person),
        })
    return rows


def make_film_genres(rng: random.Random, films: list[dict], genre_ids: list[int]) -> list[dict]:
    """От 1 до 5 разных жанров на фильм."""
    rows = []
    for film in films:
        genre_count = rng.randint(1, 5)
        for genre_id in rng.sample(genre_ids, genre_count):
            rows.append({
                "id_film_genres": len(rows) + 1,
                "id_film": film["id_film"],
                "id_genres": genre_id,
            })
    return rows


def make_roles(
    rng: random.Random,
    role_names: list[str],
    films: list[dict],
    role_type_ids: list[int],
) -> list[dict]:
    """От 5 до 20 ролей на фильм, имена ролей не повторяются."""
    available = list(role_names)
    rng.shuffle(available)
    rows = []
    for film in films:
        role_count = rng.randint(5, 20)
        for _ in range(role_count):
            if len(available) == 0:
                raise ValueError("В roles.txt не хватило имён ролей")
            rows.append({
                "id_role": len(rows) + 1,
                "name": available.pop(),
                "description": None,
                "id_role_type": rng.choice(role_type_ids),
                "id_film": film["id_film"],
            })
    return rows


def make_applications(
    rng: random.Random,
    actors: list[dict],
    roles: list[dict],
    films: list[dict],
    filmography_first: list[str],
    filmography_second: list[str],
) -> list[dict]:
    """От 5 до 7 заявок на актёра; режиссёры заявки берутся из фильма роли."""
    film_by_id = {film["id_film"]: film for film in films}
    rows = []
    for actor in actors:
        filmography = f"{rng.choice(filmography_first)} {rng.choice(filmography_second)}"
        photo = f"C:/Documents/Photos/actor/{actor['id_actor']}.jpg"
        application_count = rng.randint(5, 7)
        for _ in range(application_count):
            role = rng.choice(roles)
            film = film_by_id[role["id_film"]]
            rows.append({
                "id_application": len(rows) + 1,
                "filmography": filmography,
                "photos": photo,
                "id_actor": actor["id_actor"],
                "id_role": role["id_role"],
                "id_casting_director": film["id_casting_director"],
                "id_director": film["id_director"],
            })
    return rows


def make_first_stage(rng: random.Random, applications: list[dict]) -> list[dict]:
    """Первый этап: ровно одна запись на каждую заявку, в случайном порядке."""
    application_ids = [application["id_application"] for application in applications]
    rng.shuffle(application_ids)
    rows = []
    for application_id in application_ids:
        directors_score = rng.randint(18, 100)
        casting_score = rng.randint(18, 100)
        # Порог из оригинала: сумма двух оценок больше 100
        passed = directors_score + casting_score > 100
        rows.append({
            "id_first_stage": len(rows) + 1,
            "directors_assessment": directors_score,
            "casting_directors_assessment": casting_score,
            "passing": passing_label(passed),
            "id_application": application_id,
        })
    return rows


def make_audition(rng: random.Random, first_stage: list[dict]) -> list[dict]:
    """Прослушивание для прошедших первый этап."""
    rows = []
    for first in first_stage:
        if first["passing"] != passing_label(True):
            continue
        directors_score = rng.randint(10, 80)
        casting_score = rng.randint(10, 80)
        # Порог из оригинала: сумма двух оценок больше 100
        passed = directors_score + casting_score > 100
        rows.append({
            "id_audition": len(rows) + 1,
            "directors_assessment": directors_score,
            "casting_directors_assessment": casting_score,
            "passing": passing_label(passed),
            "id_application": first["id_application"],
        })
    return rows


def make_doubles_audition(rng: random.Random, first_stage: list[dict], audition: list[dict]) -> list[dict]:
    """Прослушивание с дублёрами и итог: получена ли роль."""
    first_by_application = {first["id_application"]: first for first in first_stage}
    rows = []
    for second in audition:
        if second["passing"] != passing_label(True):
            continue
        first = first_by_application[second["id_application"]]
        directors_score = rng.randint(20, 100)
        casting_score = rng.randint(20, 100)
        total = (
            first["directors_assessment"] + first["casting_directors_assessment"]
            + second["directors_assessment"] + second["casting_directors_assessment"]
            + directors_score + casting_score
        )
        # Порог из оригинала: сумма шести оценок за три этапа больше 400
        role_received = total > 400
        rows.append({
            "id_doubles_audition": len(rows) + 1,
            "directors_assessment": directors_score,
            "casting_directors_assessment": casting_score,
            "id_application": second["id_application"],
            "results": total,
            "getting_a_role": "Роль получена" if role_received else "Роль не получена",
        })
    return rows


def sql_value(value) -> str:
    """Превращает значение Python в литерал MySQL."""
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, datetime.date):
        return f"'{value.isoformat()}'"
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace("'", "''")
        return f"'{escaped}'"
    raise TypeError(f"Неподдерживаемый тип значения: {type(value).__name__}")


def open_output(path: Path) -> io.TextIOBase:
    """Открывает файл на запись; .gz пишется с mtime=0, чтобы повторный запуск давал тот же файл."""
    if path.suffix == ".gz":
        return io.TextIOWrapper(gzip.GzipFile(str(path), mode="wb", mtime=0), encoding="utf-8", newline="\n")
    return open(path, "w", encoding="utf-8", newline="\n")


def write_dump(path: Path, tables: list[tuple[str, list[dict]]], seed: int, batch_size: int) -> None:
    """Пишет SQL-файл: все таблицы одной транзакцией, INSERT пачками."""
    with open_output(path) as out:
        out.write(f"-- Сгенерировано source-db/seed/generate.py, seed={seed}\n")
        out.write("SET NAMES utf8mb4;\n")
        out.write("START TRANSACTION;\n\n")
        for table_name, rows in tables:
            if len(rows) == 0:
                continue
            columns = list(rows[0].keys())
            column_list = ", ".join(columns)
            for start in range(0, len(rows), batch_size):
                batch = rows[start:start + batch_size]
                values = ",\n".join(
                    "(" + ", ".join(sql_value(row[column]) for column in columns) + ")"
                    for row in batch
                )
                out.write(f"INSERT INTO {table_name} ({column_list}) VALUES\n{values};\n")
            out.write("\n")
        out.write("COMMIT;\n")


def parse_args() -> argparse.Namespace:
    """Аргументы командной строки."""
    parser = argparse.ArgumentParser(description="Генерирует SQL-файл с данными кастинга для source-db")
    parser.add_argument("--data", type=Path, required=True, help="папка с исходными txt")
    parser.add_argument("--output", type=Path, required=True, help="куда писать .sql или .sql.gz")
    parser.add_argument("--seed", type=int, default=42, help="seed генератора случайных чисел")
    return parser.parse_args()


def main() -> None:
    """Генерирует все таблицы и пишет их в файл."""
    args = parse_args()
    rng = random.Random(args.seed)
    data_dir = args.data

    actor_count = 10000
    people_count = 200
    film_count = 1000
    max_films_per_person = 6

    role_types = make_role_types()
    genres = make_genres()
    directors = make_film_people(rng, read_lines(data_dir, "director.txt"), people_count, "id_director")
    casting_directors = make_film_people(
        rng, read_lines(data_dir, "casting_dir.txt"), people_count, "id_casting_director"
    )
    actors = make_actors(
        rng,
        actor_count,
        read_lines(data_dir, "fullnames.txt"),
        read_lines(data_dir, "education.txt"),
        read_lines(data_dir, "uni.txt"),
        read_lines(data_dir, "work_experience.txt"),
    )
    films = make_films(
        rng,
        read_lines(data_dir, "films.txt"),
        film_count,
        [director["id_director"] for director in directors],
        [casting["id_casting_director"] for casting in casting_directors],
        max_films_per_person,
    )
    film_genres = make_film_genres(rng, films, [genre["id_genres"] for genre in genres])
    roles = make_roles(
        rng,
        read_lines(data_dir, "roles.txt"),
        films,
        [role_type["id_role_type"] for role_type in role_types],
    )
    applications = make_applications(
        rng, actors, roles, films, read_lines(data_dir, "f1.txt"), read_lines(data_dir, "f2.txt")
    )
    first_stage = make_first_stage(rng, applications)
    audition = make_audition(rng, first_stage)
    doubles_audition = make_doubles_audition(rng, first_stage, audition)

    # Порядок важен: сначала справочники, потом таблицы, которые на них ссылаются
    tables = [
        ("role_type", role_types),
        ("genres", genres),
        ("director", directors),
        ("casting_director", casting_directors),
        ("actor", actors),
        ("film", films),
        ("film_genres", film_genres),
        ("role", roles),
        ("application", applications),
        ("first_stage", first_stage),
        ("audition", audition),
        ("doubles_audition", doubles_audition),
    ]
    write_dump(args.output, tables, args.seed, batch_size=1000)

    for table_name, rows in tables:
        print(f"{table_name}: {len(rows)}")
    print(f"Записано в {args.output}")


if __name__ == "__main__":
    main()
