import asyncio
import logging
from typing import List
import tmdbsimple
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.database.database import init_db
from app.database.models import Movie, TVCategory
from app.database.movie_repository import movie_repository
from app.modules.data_collection.schemas.movie_data_source import MovieDataSourceResult
from app.modules.filter.flow import filter_flow
from app.modules.link_parse.flow import link_parse_flow_parses
from app.modules.link_parse.schemas import LinkParseResult, PrepareParseLinks

from app.modules.link_scraping.flow import link_scrape_flow_search
from app.modules.link_scraping.schemes.link import LinkScrapeResult
from app.services.movie_service import movie_service
from app.modules.data_collection.flow import data_collection_get_hot_flow

