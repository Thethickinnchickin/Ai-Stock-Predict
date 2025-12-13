# graphql/mutations.py

import strawberry
from typing import List
from ..config.settings import settings
from ..services.alert_service import AlertService


alert_service = AlertService()


@strawberry.type
class Mutation:
    @strawberry.mutation
    def add_symbol(self, symbol: str) -> List[str]:
        symbol = symbol.upper()
        if symbol not in settings.SYMBOLS:
            settings.SYMBOLS.append(symbol)
        return settings.SYMBOLS

    @strawberry.mutation
    async def create_alert(self, symbol: str, threshold: float, condition: str) -> bool:
        """
        condition: 'above' or 'below'
        """
        await alert_service.add_alert(symbol.upper(), threshold, condition.lower())
        return True
