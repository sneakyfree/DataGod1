"""
Lottery Winners Scraper
=======================

Comprehensive scraper for public lottery winner records from state
lottery commissions. Most states publish winner information above
certain thresholds ($600+ typically) as required by law.

Data Sources:
- State lottery commission websites
- Winner claim databases
- Prize payment records

Public Information Typically Available:
- Winner name
- City/State of residence
- Game played
- Prize amount
- Date won/claimed
- Retailer location (sometimes)

Note: Some winners can claim anonymously in certain states (DE, KS, MD,
ND, OH, SC, and a few others). This scraper collects only publicly
disclosed winners.
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from typing import Optional, List, Dict, Any
import json
import re
import logging

logger = logging.getLogger(__name__)


class LotteryGame(Enum):
    """Types of lottery games"""
    # Multi-State Games
    POWERBALL = "powerball"
    MEGA_MILLIONS = "mega_millions"
    LUCKY_FOR_LIFE = "lucky_for_life"
    CASH4LIFE = "cash4life"

    # State Draw Games
    STATE_LOTTO = "state_lotto"
    PICK_3 = "pick_3"
    PICK_4 = "pick_4"
    PICK_5 = "pick_5"
    PICK_6 = "pick_6"
    DAILY_GAME = "daily_game"
    CASH_5 = "cash_5"
    MATCH_5 = "match_5"
    FANTASY_5 = "fantasy_5"
    HIT_5 = "hit_5"
    SUPER_LOTTO = "super_lotto"

    # Instant/Scratch Games
    SCRATCH_OFF = "scratch_off"
    INSTANT_GAME = "instant_game"
    FAST_PLAY = "fast_play"

    # Raffle
    RAFFLE = "raffle"
    SECOND_CHANCE = "second_chance"

    # Keno
    KENO = "keno"
    CLUB_KENO = "club_keno"

    OTHER = "other"


class PrizeType(Enum):
    """Prize payment types"""
    JACKPOT = "jackpot"
    SECOND_PRIZE = "second_prize"
    THIRD_PRIZE = "third_prize"
    MATCH_5 = "match_5"
    MATCH_4 = "match_4"
    MATCH_3 = "match_3"
    BONUS_MATCH = "bonus_match"
    TOP_PRIZE = "top_prize"
    FREE_TICKET = "free_ticket"
    OTHER = "other"


class PaymentOption(Enum):
    """Prize payment options"""
    CASH_LUMP_SUM = "cash_lump_sum"
    ANNUITY = "annuity"
    INSTALLMENTS = "installments"
    DIRECT_PAYMENT = "direct_payment"


class ClaimStatus(Enum):
    """Claim status"""
    CLAIMED = "claimed"
    PENDING = "pending"
    UNCLAIMED = "unclaimed"
    EXPIRED = "expired"
    VERIFIED = "verified"
    PAID = "paid"


@dataclass
class LotteryWinner:
    """Lottery winner record"""
    # Winner identification
    winner_name: str
    city: Optional[str] = None
    state: Optional[str] = None
    county: Optional[str] = None

    # Prize information
    game: LotteryGame = LotteryGame.OTHER
    game_name: Optional[str] = None
    prize_amount: float = 0.0
    prize_type: PrizeType = PrizeType.OTHER

    # Dates
    win_date: Optional[date] = None
    draw_date: Optional[date] = None
    claim_date: Optional[date] = None

    # Ticket information
    ticket_number: Optional[str] = None
    winning_numbers: Optional[str] = None

    # Retailer information
    retailer_name: Optional[str] = None
    retailer_address: Optional[str] = None
    retailer_city: Optional[str] = None
    retailer_state: Optional[str] = None

    # Payment details
    payment_option: PaymentOption = PaymentOption.CASH_LUMP_SUM
    cash_value: Optional[float] = None
    annuity_value: Optional[float] = None

    # Status
    claim_status: ClaimStatus = ClaimStatus.CLAIMED

    # Source tracking
    source_state: Optional[str] = None
    source_url: Optional[str] = None
    source_system: Optional[str] = None
    retrieved_at: datetime = field(default_factory=datetime.now)
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchCriteria:
    """Search criteria for lottery winners"""
    winner_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    game: Optional[LotteryGame] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


@dataclass
class SearchResult:
    """Search result container"""
    winners: List[LotteryWinner] = field(default_factory=list)
    total_count: int = 0
    page: int = 1
    page_size: int = 100
    has_more: bool = False
    search_criteria: Optional[SearchCriteria] = None
    search_time_ms: int = 0
    source_system: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class BaseLotteryAPI:
    """Base class for state lottery APIs"""

    STATE_CODE: str = ""
    STATE_NAME: str = ""
    BASE_URL: str = ""
    API_URL: str = ""
    SYSTEM_NAME: str = ""

    # Minimum prize amount publicly reported (typically $600)
    MIN_REPORTABLE_PRIZE: float = 600.0

    # Rate limiting
    REQUEST_DELAY: float = 1.0

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; DataGod/1.0; Public Records Research)"
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _fetch_json(self, url: str, params: Optional[Dict] = None) -> Dict:
        """Fetch JSON data from URL"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async with.")

        await asyncio.sleep(self.REQUEST_DELAY)

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()

    async def _fetch_html(self, url: str, params: Optional[Dict] = None) -> str:
        """Fetch HTML content from URL"""
        if not self.session:
            raise RuntimeError("Session not initialized. Use async with.")

        await asyncio.sleep(self.REQUEST_DELAY)

        async with self.session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.text()

    def _parse_amount(self, amount_str: str) -> float:
        """Parse currency string to float"""
        if not amount_str:
            return 0.0
        cleaned = re.sub(r'[^\d.]', '', str(amount_str))
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string"""
        if not date_str:
            return None
        formats = [
            "%Y-%m-%d",
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%B %d, %Y",
            "%b %d, %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _classify_game(self, game_name: str) -> LotteryGame:
        """Classify game type from name"""
        if not game_name:
            return LotteryGame.OTHER

        name_lower = game_name.lower()

        if "powerball" in name_lower:
            return LotteryGame.POWERBALL
        elif "mega millions" in name_lower or "megamillions" in name_lower:
            return LotteryGame.MEGA_MILLIONS
        elif "lucky for life" in name_lower:
            return LotteryGame.LUCKY_FOR_LIFE
        elif "cash4life" in name_lower or "cash 4 life" in name_lower:
            return LotteryGame.CASH4LIFE
        elif "scratch" in name_lower or "instant" in name_lower:
            return LotteryGame.SCRATCH_OFF
        elif "pick 3" in name_lower or "pick-3" in name_lower:
            return LotteryGame.PICK_3
        elif "pick 4" in name_lower or "pick-4" in name_lower:
            return LotteryGame.PICK_4
        elif "pick 5" in name_lower or "pick-5" in name_lower:
            return LotteryGame.PICK_5
        elif "pick 6" in name_lower or "pick-6" in name_lower:
            return LotteryGame.PICK_6
        elif "cash 5" in name_lower or "cash5" in name_lower:
            return LotteryGame.CASH_5
        elif "fantasy 5" in name_lower:
            return LotteryGame.FANTASY_5
        elif "keno" in name_lower:
            return LotteryGame.KENO
        elif "raffle" in name_lower:
            return LotteryGame.RAFFLE
        elif "lotto" in name_lower:
            return LotteryGame.STATE_LOTTO

        return LotteryGame.OTHER

    async def search_winners(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        game: Optional[LotteryGame] = None,
        min_amount: Optional[float] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search for lottery winners - override in subclass"""
        raise NotImplementedError

    async def get_recent_winners(
        self,
        days: int = 30,
        min_amount: float = 10000,
        max_results: int = 100
    ) -> SearchResult:
        """Get recent winners above threshold"""
        raise NotImplementedError

    async def get_jackpot_winners(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Get jackpot winners"""
        raise NotImplementedError


class CaliforniaLotteryAPI(BaseLotteryAPI):
    """California State Lottery API"""

    STATE_CODE = "CA"
    STATE_NAME = "California"
    BASE_URL = "https://www.calottery.com"
    API_URL = "https://www.calottery.com/api/winners"
    SYSTEM_NAME = "California Lottery"

    MIN_REPORTABLE_PRIZE = 600.0

    async def search_winners(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        game: Optional[LotteryGame] = None,
        min_amount: Optional[float] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search California lottery winners"""
        import time
        start_time = time.time()

        params = {"limit": min(max_results, 100)}

        if name:
            params["name"] = name
        if city:
            params["city"] = city
        if min_amount:
            params["minPrize"] = min_amount
        if start_date:
            params["startDate"] = start_date.strftime("%Y-%m-%d")
        if end_date:
            params["endDate"] = end_date.strftime("%Y-%m-%d")

        try:
            data = await self._fetch_json(self.API_URL, params=params)
        except Exception as e:
            logger.error(f"California lottery search failed: {e}")
            return SearchResult(
                winners=[],
                total_count=0,
                warnings=[str(e)],
            )

        winners = []
        for item in data.get("winners", [])[:max_results]:
            winner = LotteryWinner(
                winner_name=item.get("name", ""),
                city=item.get("city"),
                state="CA",
                game=self._classify_game(item.get("game", "")),
                game_name=item.get("game"),
                prize_amount=self._parse_amount(item.get("prize", "0")),
                win_date=self._parse_date(item.get("winDate", "")),
                claim_date=self._parse_date(item.get("claimDate", "")),
                retailer_name=item.get("retailer"),
                retailer_city=item.get("retailerCity"),
                source_state="CA",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            winners.append(winner)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            winners=winners,
            total_count=data.get("total", len(winners)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                winner_name=name,
                city=city,
                game=game,
                min_amount=min_amount,
                start_date=start_date,
                end_date=end_date,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def get_recent_winners(
        self,
        days: int = 30,
        min_amount: float = 10000,
        max_results: int = 100
    ) -> SearchResult:
        """Get recent California lottery winners"""
        from datetime import timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        return await self.search_winners(
            start_date=start_date,
            end_date=end_date,
            min_amount=min_amount,
            max_results=max_results
        )

    async def get_jackpot_winners(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Get California jackpot winners"""
        return await self.search_winners(
            min_amount=1000000,
            start_date=start_date,
            end_date=end_date,
            max_results=max_results
        )


class TexasLotteryAPI(BaseLotteryAPI):
    """Texas Lottery Commission API"""

    STATE_CODE = "TX"
    STATE_NAME = "Texas"
    BASE_URL = "https://www.txlottery.org"
    API_URL = "https://www.txlottery.org/export/sites/lottery/Winners"
    SYSTEM_NAME = "Texas Lottery"

    MIN_REPORTABLE_PRIZE = 600.0

    async def search_winners(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        game: Optional[LotteryGame] = None,
        min_amount: Optional[float] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search Texas lottery winners"""
        import time
        start_time = time.time()

        params = {"pageSize": min(max_results, 100)}

        if city:
            params["city"] = city
        if min_amount:
            params["minPrize"] = int(min_amount)

        try:
            data = await self._fetch_json(f"{self.API_URL}/winners.json", params=params)
        except Exception as e:
            logger.error(f"Texas lottery search failed: {e}")
            return SearchResult(
                winners=[],
                total_count=0,
                warnings=[str(e)],
            )

        winners = []
        for item in data.get("winners", [])[:max_results]:
            # Filter by name if specified
            if name and name.lower() not in item.get("name", "").lower():
                continue

            winner = LotteryWinner(
                winner_name=item.get("name", ""),
                city=item.get("city"),
                state="TX",
                game=self._classify_game(item.get("game", "")),
                game_name=item.get("game"),
                prize_amount=self._parse_amount(item.get("amount", "0")),
                win_date=self._parse_date(item.get("date", "")),
                retailer_name=item.get("retailer"),
                retailer_city=item.get("retailerCity"),
                source_state="TX",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            winners.append(winner)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            winners=winners,
            total_count=len(winners),
            search_criteria=SearchCriteria(
                winner_name=name,
                city=city,
                game=game,
                min_amount=min_amount,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )

    async def get_recent_winners(
        self,
        days: int = 30,
        min_amount: float = 10000,
        max_results: int = 100
    ) -> SearchResult:
        """Get recent Texas lottery winners"""
        from datetime import timedelta
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        return await self.search_winners(
            start_date=start_date,
            end_date=end_date,
            min_amount=min_amount,
            max_results=max_results
        )


class FloridaLotteryAPI(BaseLotteryAPI):
    """Florida Lottery API"""

    STATE_CODE = "FL"
    STATE_NAME = "Florida"
    BASE_URL = "https://www.flalottery.com"
    API_URL = "https://www.flalottery.com/exptkt/winners"
    SYSTEM_NAME = "Florida Lottery"

    MIN_REPORTABLE_PRIZE = 600.0

    async def search_winners(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        game: Optional[LotteryGame] = None,
        min_amount: Optional[float] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search Florida lottery winners"""
        import time
        start_time = time.time()

        params = {"limit": min(max_results, 100)}

        if city:
            params["city"] = city
        if min_amount:
            params["minAmount"] = int(min_amount)

        try:
            data = await self._fetch_json(self.API_URL, params=params)
        except Exception as e:
            logger.error(f"Florida lottery search failed: {e}")
            return SearchResult(
                winners=[],
                total_count=0,
                warnings=[str(e)],
            )

        winners = []
        for item in data.get("winners", [])[:max_results]:
            if name and name.lower() not in item.get("winner", "").lower():
                continue

            winner = LotteryWinner(
                winner_name=item.get("winner", ""),
                city=item.get("city"),
                state="FL",
                county=item.get("county"),
                game=self._classify_game(item.get("game", "")),
                game_name=item.get("game"),
                prize_amount=self._parse_amount(item.get("prize", "0")),
                win_date=self._parse_date(item.get("winDate", "")),
                claim_date=self._parse_date(item.get("claimDate", "")),
                retailer_name=item.get("retailerName"),
                retailer_address=item.get("retailerAddress"),
                retailer_city=item.get("retailerCity"),
                source_state="FL",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            winners.append(winner)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            winners=winners,
            total_count=data.get("total", len(winners)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                winner_name=name,
                city=city,
                game=game,
                min_amount=min_amount,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


class NewYorkLotteryAPI(BaseLotteryAPI):
    """New York Lottery API"""

    STATE_CODE = "NY"
    STATE_NAME = "New York"
    BASE_URL = "https://nylottery.ny.gov"
    API_URL = "https://nylottery.ny.gov/api/winners"
    SYSTEM_NAME = "New York Lottery"

    MIN_REPORTABLE_PRIZE = 600.0

    async def search_winners(
        self,
        name: Optional[str] = None,
        city: Optional[str] = None,
        game: Optional[LotteryGame] = None,
        min_amount: Optional[float] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        max_results: int = 100
    ) -> SearchResult:
        """Search New York lottery winners"""
        import time
        start_time = time.time()

        params = {"pageSize": min(max_results, 100)}

        if city:
            params["city"] = city
        if min_amount:
            params["minPrize"] = int(min_amount)

        try:
            data = await self._fetch_json(self.API_URL, params=params)
        except Exception as e:
            logger.error(f"New York lottery search failed: {e}")
            return SearchResult(
                winners=[],
                total_count=0,
                warnings=[str(e)],
            )

        winners = []
        for item in data.get("winners", [])[:max_results]:
            if name and name.lower() not in item.get("name", "").lower():
                continue

            winner = LotteryWinner(
                winner_name=item.get("name", ""),
                city=item.get("city"),
                state="NY",
                county=item.get("county"),
                game=self._classify_game(item.get("game", "")),
                game_name=item.get("game"),
                prize_amount=self._parse_amount(item.get("amount", "0")),
                win_date=self._parse_date(item.get("drawDate", "")),
                claim_date=self._parse_date(item.get("claimDate", "")),
                retailer_name=item.get("retailer"),
                source_state="NY",
                source_url=self.BASE_URL,
                source_system=self.SYSTEM_NAME,
                raw_data=item,
            )
            winners.append(winner)

        search_time = int((time.time() - start_time) * 1000)

        return SearchResult(
            winners=winners,
            total_count=data.get("total", len(winners)),
            has_more=data.get("hasMore", False),
            search_criteria=SearchCriteria(
                winner_name=name,
                city=city,
                game=game,
                min_amount=min_amount,
            ),
            search_time_ms=search_time,
            source_system=self.SYSTEM_NAME,
        )


# State lottery API registry
STATE_LOTTERY_APIS: Dict[str, type] = {
    "CA": CaliforniaLotteryAPI,
    "TX": TexasLotteryAPI,
    "FL": FloridaLotteryAPI,
    "NY": NewYorkLotteryAPI,
}


def get_lottery_api(state: str) -> Optional[BaseLotteryAPI]:
    """Get lottery API for a state"""
    api_class = STATE_LOTTERY_APIS.get(state.upper())
    if api_class:
        return api_class()
    return None


# Convenience functions

def search_lottery_winners(
    state: str,
    name: Optional[str] = None,
    city: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_results: int = 100
) -> SearchResult:
    """Search lottery winners in a state"""
    async def _search():
        api = get_lottery_api(state)
        if not api:
            return SearchResult(
                winners=[],
                total_count=0,
                warnings=[f"No lottery API available for state: {state}"],
            )
        async with api:
            return await api.search_winners(
                name=name,
                city=city,
                min_amount=min_amount,
                max_results=max_results
            )
    return asyncio.run(_search())


def get_recent_lottery_winners(
    state: str,
    days: int = 30,
    min_amount: float = 10000,
    max_results: int = 100
) -> SearchResult:
    """Get recent lottery winners in a state"""
    async def _get():
        api = get_lottery_api(state)
        if not api:
            return SearchResult(
                winners=[],
                total_count=0,
                warnings=[f"No lottery API available for state: {state}"],
            )
        async with api:
            return await api.get_recent_winners(
                days=days,
                min_amount=min_amount,
                max_results=max_results
            )
    return asyncio.run(_get())


def get_jackpot_winners(
    state: str,
    max_results: int = 100
) -> SearchResult:
    """Get jackpot winners (>$1M) in a state"""
    async def _get():
        api = get_lottery_api(state)
        if not api:
            return SearchResult(
                winners=[],
                total_count=0,
                warnings=[f"No lottery API available for state: {state}"],
            )
        async with api:
            return await api.get_jackpot_winners(max_results=max_results)
    return asyncio.run(_get())


def search_all_states_lottery_winners(
    name: Optional[str] = None,
    city: Optional[str] = None,
    min_amount: Optional[float] = None,
    max_results_per_state: int = 50
) -> List[SearchResult]:
    """Search lottery winners across all available states"""
    async def _search_all():
        results = []
        for state_code, api_class in STATE_LOTTERY_APIS.items():
            try:
                async with api_class() as api:
                    result = await api.search_winners(
                        name=name,
                        city=city,
                        min_amount=min_amount,
                        max_results=max_results_per_state
                    )
                    results.append(result)
            except Exception as e:
                logger.error(f"Error searching {state_code}: {e}")
                results.append(SearchResult(
                    winners=[],
                    total_count=0,
                    warnings=[f"{state_code}: {str(e)}"],
                ))
        return results
    return asyncio.run(_search_all())
