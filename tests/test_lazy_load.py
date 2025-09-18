import pytest

from app.database.database import init_db_sync
from app.database.models import Movie, MovieType
init_db_sync()

@pytest.mark.asycio
def test_lazy_load_():
    movie=Movie(title_season='',year='2024',movie_type=MovieType.MOVIE)
    movie.register_lazy_field('current_episodes',lambda self:'草泥马')

