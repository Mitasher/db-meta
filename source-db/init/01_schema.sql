SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS role_type (
    id_role_type INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(15) DEFAULT NULL,
    PRIMARY KEY (id_role_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS genres (
    id_genres INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(20) DEFAULT NULL,
    PRIMARY KEY (id_genres)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS director (
    id_director INT UNSIGNED NOT NULL AUTO_INCREMENT,
    surname VARCHAR(30) DEFAULT NULL,
    name VARCHAR(20) DEFAULT NULL,
    patronymic VARCHAR(20) DEFAULT NULL,
    date_of_birth DATE DEFAULT NULL,
    passport_number VARCHAR(11) DEFAULT NULL,
    filmography TEXT DEFAULT NULL,
    PRIMARY KEY (id_director)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS casting_director (
    id_casting_director INT UNSIGNED NOT NULL AUTO_INCREMENT,
    surname VARCHAR(30) DEFAULT NULL,
    name VARCHAR(20) DEFAULT NULL,
    patronymic VARCHAR(20) DEFAULT NULL,
    date_of_birth DATE DEFAULT NULL,
    passport_number VARCHAR(11) DEFAULT NULL,
    filmography TEXT DEFAULT NULL,
    PRIMARY KEY (id_casting_director)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS actor (
    id_actor INT UNSIGNED NOT NULL AUTO_INCREMENT,
    surname VARCHAR(30) DEFAULT NULL,
    name VARCHAR(20) DEFAULT NULL,
    patronymic VARCHAR(20) DEFAULT NULL,
    date_of_birth DATE DEFAULT NULL,
    passport_number VARCHAR(11) DEFAULT NULL,
    education TEXT DEFAULT NULL,
    work_experience TEXT DEFAULT NULL,
    PRIMARY KEY (id_actor)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS film (
    id_film INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) DEFAULT NULL,
    id_director INT UNSIGNED NOT NULL,
    id_casting_director INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_film),
    FOREIGN KEY (id_director) REFERENCES director (id_director),
    FOREIGN KEY (id_casting_director) REFERENCES casting_director (id_casting_director)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS film_genres (
    id_film_genres INT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_film INT UNSIGNED NOT NULL,
    id_genres INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_film_genres),
    UNIQUE KEY uq_film_genres (id_film, id_genres),
    FOREIGN KEY (id_film) REFERENCES film (id_film),
    FOREIGN KEY (id_genres) REFERENCES genres (id_genres)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS role (
    id_role INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name VARCHAR(30) DEFAULT NULL,
    description TEXT DEFAULT NULL,
    id_role_type INT UNSIGNED NOT NULL,
    id_film INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_role),
    FOREIGN KEY (id_role_type) REFERENCES role_type (id_role_type),
    FOREIGN KEY (id_film) REFERENCES film (id_film)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS application (
    id_application INT UNSIGNED NOT NULL AUTO_INCREMENT,
    filmography TEXT DEFAULT NULL,
    photos VARCHAR(200) DEFAULT NULL,
    id_actor INT UNSIGNED NOT NULL,
    id_role INT UNSIGNED NOT NULL,
    id_casting_director INT UNSIGNED NOT NULL,
    id_director INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_application),
    FOREIGN KEY (id_actor) REFERENCES actor (id_actor),
    FOREIGN KEY (id_role) REFERENCES role (id_role),
    FOREIGN KEY (id_casting_director) REFERENCES casting_director (id_casting_director),
    FOREIGN KEY (id_director) REFERENCES director (id_director)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS first_stage (
    id_first_stage INT UNSIGNED NOT NULL AUTO_INCREMENT,
    directors_assessment TINYINT UNSIGNED DEFAULT NULL,
    casting_directors_assessment TINYINT UNSIGNED DEFAULT NULL,
    passing VARCHAR(20) DEFAULT NULL,
    id_application INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_first_stage),
    FOREIGN KEY (id_application) REFERENCES application (id_application)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audition (
    id_audition INT UNSIGNED NOT NULL AUTO_INCREMENT,
    directors_assessment TINYINT UNSIGNED DEFAULT NULL,
    casting_directors_assessment TINYINT UNSIGNED DEFAULT NULL,
    passing VARCHAR(20) DEFAULT NULL,
    id_application INT UNSIGNED NOT NULL,
    PRIMARY KEY (id_audition),
    FOREIGN KEY (id_application) REFERENCES application (id_application)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS doubles_audition (
    id_doubles_audition INT UNSIGNED NOT NULL AUTO_INCREMENT,
    directors_assessment TINYINT UNSIGNED DEFAULT NULL,
    casting_directors_assessment TINYINT UNSIGNED DEFAULT NULL,
    id_application INT UNSIGNED NOT NULL,
    results SMALLINT UNSIGNED DEFAULT NULL,
    getting_a_role VARCHAR(20) DEFAULT NULL,
    PRIMARY KEY (id_doubles_audition),
    FOREIGN KEY (id_application) REFERENCES application (id_application)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
