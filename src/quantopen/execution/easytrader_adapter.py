from typing import List, Optional
from loguru import logger
from quantopen.execution.api import TradeExecutor, Balance, Position

class EasyTraderExecutor(TradeExecutor):
    def __init__(self):
        self._user = None
        
    def connect(self, client="xq", **kwargs):
        """
        Connect to easytrader.
        client: 'xq', 'ht', 'ths', 'yh', etc.
        kwargs: passed to user.prepare() -> user/password/cookie_path etc.
                For 'xq', often needs 'json_config_path' or no args (scan QR).
        """
        import easytrader
        
        logger.info(f"Connecting to EasyTrader ({client})...")
        try:
            self._user = easytrader.use(client)
            self._user.prepare(**kwargs)
            logger.success(f"Connected to {client}")
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            raise

    def get_balance(self) -> Balance:
        b = self._user.balance
        # easytrader balance structure varies.
        # XQ: {'asset_balance': X, 'current_balance': Y, 'market_value': Z}
        # HT: {'资金余额': ..., '可用资金': ...}
        # We need normalization. For now assuming standard property access from easytrader objects
        
        # Let's try flexible mapping
        assets = 0.0
        cash = 0.0
        mkt = 0.0
        
        # Determine format based on keys
        # This is a bit tricky universal mapping. 
        # For XQ (simulation):
        if isinstance(b, dict):
             # XQ style
             assets = float(b.get("asset_balance", 0))
             cash = float(b.get("current_balance", 0) or b.get("enable_balance", 0))
             mkt = float(b.get("market_value", 0))
        # TODO: Handle other brokers
        
        return Balance(total_assets=assets, available_cash=cash, market_value=mkt)

    def get_positions(self) -> List[Position]:
        raw_pos = self._user.position
        ret = []
        for p in raw_pos:
            # XQ: stock_code, current_amount, enable_amount, last_price, market_value
            sym = p.get("stock_code", "")
            if not sym: continue
            
            # Normalize symbol? XQ returns SH600519
            # Our system uses 600519. 
            # But let's keep it as adapter returns. The strategy/caller handles mapping?
            # Or map here. Let's map to pure digits if possible.
            import re
            m = re.search(r"\d{6}", sym)
            clean_sym = m.group(0) if m else sym
            
            vol = int(p.get("current_amount", 0))
            avail = int(p.get("enable_amount", 0))
            price = float(p.get("last_price", 0) or p.get("cost_price", 0))
            mval = float(p.get("market_value", 0))
            
            ret.append(Position(symbol=clean_sym, volume=vol, available=avail, price=price, market_value=mval))
        return ret

    def buy(self, symbol: str, price: float, amount: int) -> Optional[str]:
        # easytrader buy(security, price, amount)
        # For XQ, symbol needs prefix? easytrader handles it usually? 
        # XQ needs SH/SZ. 
        # We should helper func to add prefix.
        
        # 简单处理：如果全是数字，尝试加后缀/前缀？
        # Easytrader usually expects code like '600000'.
        
        logger.info(f"BUY {symbol} {amount} @ {price}")
        try:
            # enturst = order info
            resp = self._user.buy(symbol, price=price, amount=amount)
            logger.info(f"Buy Resp: {resp}")
            # return order id
            if isinstance(resp, dict):
                 return resp.get("entrust_no", None) # XQ
            return str(resp)
        except Exception as e:
            logger.error(f"Buy failed: {e}")
            return None

    def sell(self, symbol: str, price: float, amount: int) -> Optional[str]:
        logger.info(f"SELL {symbol} {amount} @ {price}")
        try:
            resp = self._user.sell(symbol, price=price, amount=amount)
            logger.info(f"Sell Resp: {resp}")
            if isinstance(resp, dict):
                 return resp.get("entrust_no", None)
            return str(resp)
        except Exception as e:
            logger.error(f"Sell failed: {e}")
            return None
    
    def cancel_all(self):
        # self._user.cancel_all_entrust() # not standard?
        # easytrader has cancel_entrust
        pass
