CREATE DATABASE IF NOT EXISTS labdb;
USE labdb;

--tabella registi
CREATE TABLE IF NOT EXISTS directors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL UNIQUE,
    eta INT NOT NULL
);


--tabella dei film
CREATE TABLE IF NOT EXISTS movies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titolo VARCHAR(255) NOT NULL UNIQUE,
    anno INT NOT NULL,
    genere VARCHAR(255) NOT NULL,
    director_id INT,
    CONSTRAINT fk_movies_director
        FOREIGN KEY (director_id) REFERENCES directors(id)
        ON DELETE SET NULL
);

--tabella delle piattaforme
CREATE TABLE IF NOT EXISTS platforms (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL UNIQUE
);

--tabella film-piattaforme
CREATE TABLE IF NOT EXISTS movie_platform (
    movie_id INT NOT NULL,
    platform_id INT NOT NULL,
    CONSTRAINT fk_movieplatform_movie
        FOREIGN KEY (movie_id) REFERENCES movies(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_movieplatform_platform
        FOREIGN KEY (platform_id) REFERENCES platforms(id)
        ON DELETE CASCADE,
    CONSTRAINT pk_movieplatform PRIMARY KEY (movie_id, platform_id)
);