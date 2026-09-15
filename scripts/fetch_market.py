#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_market.py — 模块 A 外围市场行情采集（P0）

「盘前雷达」skill 的数据采集层之一。
采集 A 股盘前判断所需的全球外围行情，输出结构化 JSON。

设计原则：
  1. 纯标准库（urllib），零第三方依赖，开箱即用。
  2. 三级降级：腾讯直连 -> 新浪直连 -> 标记缺失（None）。
  3. 无 key、无注册，公开接口。
  4. 涨跌幅统一保留符号（正=涨/利多方向，负=跌），配色/方向判断交给上层。

用法：
  python3 fetch_market.py            # 打印 JSON 到 stdout
  python3 fetch_market.py --pretty   # 美化打印
"""

import json
import sys
import urllib.request
import urllib.parse
import time

# ---------------------------------------------------------------------------
# 基础 HTTP 工具
# ---------------------------------------------------------------------------
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
TIMEOUT = 8


def http_get(url, referer=None, decode="gbk", retries=2):
    """GET 请求，带重试。返回解码后的文本；失败返回 None。"""
    for attempt in range(retries + 1):
        try:
            headers = {"User-Agent": UA}
            if referer:
                headers["Referer"] = referer
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                raw = resp.read()
            return raw.decode(decode, "ignore")
        except Exception:
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
    return None


# ---------------------------------------------------------------------------
# 腾讯 qt.gtimg.cn — 美股指数 / 港股指数
#   字段(split '~')：1名称 3现价 4昨收 5今开 30时间 31涨跌额 32涨跌幅 33最高 34最低 35货币
# ---------------------------------------------------------------------------
TENCENT_CODES = {
    "usINX":  "标普500",
    "usDJI":  "道琼斯",
    "usIXIC": "纳斯达克",
    "usHXC":  "中概金龙",
    "hkHSI":  "恒生指数",
    # 费半(SOX) 腾讯无此代码（usSOX 返回空），改用新浪 gb_$sox，见 SINA_GB
}


def fetch_tencent_indices(codes):
    """一次拉取多个腾讯指数代码。返回 {code: dict}。"""
    url = "https://qt.gtimg.cn/q=" + ",".join(codes)
    text = http_get(url)
    if not text:
        return {}
    result = {}
    for line in text.strip().split(";"):
        line = line.strip()
        if not line or '="' not in line:
            continue
        # 形如 v_usINX="..."
        code = line.split("=")[0].replace("v_", "").strip()
        body = line.split('"')[1] if '"' in line else ""
        f = body.split("~")
        if len(f) < 35 or not f[3]:
            continue
        try:
            result[code] = {
                "name": f[1],
                "code": f[2],
                "price": _f(f[3]),
                "prev_close": _f(f[4]),
                "change": _f(f[31]),
                "change_pct": _f(f[32]),
                "high": _f(f[33]),
                "low": _f(f[34]),
                "time": f[30],
                "currency": "USD" if code.startswith("us") else ("HKD" if code.startswith("hk") else ""),
                "source": "tencent",
            }
        except (ValueError, IndexError):
            continue
    return result


# ---------------------------------------------------------------------------
# 新浪 hq.sinajs.cn — 恒生科技(rt_hk) / 外盘期货(hf_) / 外汇(fx_) / 美元指数(DINIW)
# ---------------------------------------------------------------------------
# rt_hk 格式(split ',')：0代码 1名称 2今开 3昨收 4最高 5最低 6现价 7涨跌额 8涨跌幅 17日期 18时间
SINA_RT_HK = {
    "rt_hkHSTECH": "恒生科技指数",
}

# hf_ 外盘期货格式(split ',')：0现价 4最高 5最低 6时间 7昨收 12日期 13名称
# 涨跌额/涨跌幅需自算
SINA_HF = {
    "hf_CHA50CFD": "富时中国A50期货",
    "hf_ES":       "标普500指数期货",
    "hf_NQ":       "纳斯达克指数期货",
    "hf_VX":       "VIX恐慌指数",
    "hf_CL":       "纽约原油(WTI)",
    "hf_GC":       "纽约黄金",
    "hf_HG":       "伦铜",
}

# fx_ 外汇格式(split ',')：0时间 1现价 3昨收 9名称 17日期
# 涨跌额/涨跌幅需自算
SINA_FX = {
    "fx_susdcnh": "离岸人民币",
    "DINIW":      "美元指数",  # 美元指数与 fx 同格式(名称在[9])
}

# gb_ 美股指数格式(split ',')：
#   0名称 1现价 2涨跌幅(%) 3时间 4涨跌额 5开盘 6最高 7最低
# 费城半导体指数(SOX)：腾讯无对应代码，新浪 gb_$sox 可用
SINA_GB = {
    "gb_$sox": "费城半导体",
}


def _f(s):
    """安全转 float，空/异常返回 None。"""
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _calc_change(price, prev):
    """由现价和昨收计算涨跌额/涨跌幅。"""
    if price is None or prev is None or prev == 0:
        return None, None
    chg = round(price - prev, 4)
    pct = round(chg / prev * 100, 4)
    return chg, pct


def fetch_sina_rt_hk(codes):
    """新浪港股指数 rt_hkXXX。返回 {code: dict}。"""
    url = "https://hq.sinajs.cn/list=" + ",".join(codes)
    text = http_get(url, referer="https://finance.sina.com.cn")
    if not text:
        return {}
    result = {}
    for line in text.strip().split("\n"):
        line = line.strip()
        if '="' not in line:
            continue
        var = line.split("=")[0].replace("var hq_str_", "").strip()
        body = line.split('"')[1] if '"' in line else ""
        f = body.split(",")
        if len(f) < 18 or not f[2]:
            continue
        result[var] = {
            "name": f[1],
            "code": f[0],
            "price": _f(f[6]),
            "prev_close": _f(f[3]),
            "change": _f(f[7]),
            "change_pct": _f(f[8]),
            "high": _f(f[4]),
            "low": _f(f[5]),
            "time": f"{f[17]} {f[18]}".strip() if len(f) > 18 else f[17],
            "currency": "HKD",
            "source": "sina",
        }
    return result


def fetch_sina_hf(codes):
    """新浪外盘期货 hf_XXX。涨跌自算。返回 {code: dict}。"""
    url = "https://hq.sinajs.cn/list=" + ",".join(codes)
    text = http_get(url, referer="https://finance.sina.com.cn")
    if not text:
        return {}
    result = {}
    for line in text.strip().split("\n"):
        line = line.strip()
        if '="' not in line:
            continue
        var = line.split("=")[0].replace("var hq_str_", "").strip()
        body = line.split('"')[1] if '"' in line else ""
        f = body.split(",")
        if len(f) < 14 or not f[0]:
            continue
        price = _f(f[0])
        prev = _f(f[7])
        chg, pct = _calc_change(price, prev)
        result[var] = {
            "name": f[13],
            "code": var,
            "price": price,
            "prev_close": prev,
            "change": chg,
            "change_pct": pct,
            "high": _f(f[4]),
            "low": _f(f[5]),
            "time": f"{f[12]} {f[6]}".strip(),
            "currency": "",
            "source": "sina",
        }
    return result


def fetch_sina_fx(codes):
    """新浪外汇 fx_XXX / 美元指数 DINIW。涨跌自算。返回 {code: dict}。"""
    url = "https://hq.sinajs.cn/list=" + ",".join(codes)
    text = http_get(url, referer="https://finance.sina.com.cn")
    if not text:
        return {}
    result = {}
    for line in text.strip().split("\n"):
        line = line.strip()
        if '="' not in line:
            continue
        var = line.split("=")[0].replace("var hq_str_", "").strip()
        body = line.split('"')[1] if '"' in line else ""
        f = body.split(",")
        if len(f) < 10 or not f[1]:
            continue
        price = _f(f[1])
        prev = _f(f[3])
        chg, pct = _calc_change(price, prev)
        # 时间：f[0] 为时间；日期在 fx 子类为 f[17]、DINIW 为 f[10]
        date_str = f[17] if len(f) > 17 else (f[10] if len(f) > 10 else "")
        time_str = f[0]
        result[var] = {
            "name": f[9],
            "code": var,
            "price": price,
            "prev_close": prev,
            "change": chg,
            "change_pct": pct,
            "high": None,
            "low": None,
            "time": f"{date_str} {time_str}".strip(),
            "currency": "",
            "source": "sina",
        }
    return result


def fetch_sina_gb(codes):
    """新浪美股指数 gb_$XXX（费城半导体 SOX）。返回 {code: dict}。"""
    url = "https://hq.sinajs.cn/list=" + ",".join(codes)
    text = http_get(url, referer="https://finance.sina.com.cn")
    if not text:
        return {}
    result = {}
    for line in text.strip().split("\n"):
        line = line.strip()
        if '="' not in line:
            continue
        var = line.split("=")[0].replace("var hq_str_", "").strip()
        body = line.split('"')[1] if '"' in line else ""
        f = body.split(",")
        if len(f) < 8 or not f[1]:
            continue
        price = _f(f[1])
        chg = _f(f[4])
        prev = round(price - chg, 4) if (price is not None and chg is not None) else None
        result[var] = {
            "name": SINA_GB.get(var, f[0]),
            "code": var,
            "price": price,
            "prev_close": prev,
            "change": chg,
            "change_pct": _f(f[2]),
            "high": _f(f[6]),
            "low": _f(f[7]),
            "time": f[3],
            "currency": "USD",
            "source": "sina",
        }
    return result


# ---------------------------------------------------------------------------
# 东方财富 — 美国/中国国债收益率（RPTA_WEB_TREASURYYIELD）
#   字段：EMG00001310=美国10年  EMG00001306=美国2年  EMM00166466=中国10年
#   单位：%（如 4.73 表示 4.73%），日频数据
# ---------------------------------------------------------------------------
DC = "https://datacenter-web.eastmoney.com/api/data/v1/get"


def fetch_ust_yield():
    """美国10年期国债收益率（顺带中国10年，可算中美利差）。"""
    params = {
        "reportName": "RPTA_WEB_TREASURYYIELD",
        "columns": "ALL",
        "pageSize": "2",
        "pageNumber": "1",
        "sortColumns": "SOLAR_DATE",
        "sortTypes": "-1",
        "source": "WEB",
        "client": "WEB",
    }
    url = DC + "?" + urllib.parse.urlencode(params)
    text = http_get(url, decode="utf-8")
    if not text:
        return {}
    try:
        rows = json.loads(text).get("result", {}).get("data") or []
    except (ValueError, AttributeError):
        return {}
    if not rows:
        return {}
    latest = rows[0]
    prev = rows[1] if len(rows) > 1 else {}
    us10 = latest.get("EMG00001310")
    us2 = latest.get("EMG00001306")
    cn10 = latest.get("EMM00166466")
    us10_prev = prev.get("EMG00001310")
    change = None
    if us10 is not None and us10_prev is not None:
        change = round(us10 - us10_prev, 3)
    return {
        "name": "美国10年期国债收益率",
        "date": (latest.get("SOLAR_DATE") or "")[:10],
        "us10y": us10,
        "us2y": us2,
        "cn10y": cn10,
        "change": change,  # 收益率日变化（百分点）
        "source": "eastmoney",
    }


# ---------------------------------------------------------------------------
# 汇总
# ---------------------------------------------------------------------------
def collect():
    """采集全部外围行情，返回结构化 dict。"""
    data = {}
    # 1. 腾讯：美股三大指数 + 恒指
    data.update(fetch_tencent_indices(list(TENCENT_CODES.keys())))
    # 2. 新浪：恒生科技
    data.update(fetch_sina_rt_hk(list(SINA_RT_HK.keys())))
    # 2b. 新浪：费城半导体指数（腾讯无此代码）
    data.update(fetch_sina_gb(list(SINA_GB.keys())))
    # 3. 新浪：外盘期货（A50/标普期货/纳指期货/VIX/原油/黄金）
    data.update(fetch_sina_hf(list(SINA_HF.keys())))
    # 4. 新浪：外汇（离岸人民币/美元指数）
    data.update(fetch_sina_fx(list(SINA_FX.keys())))
    # 5. 东财：美债收益率（10Y/2Y + 中国10Y）
    data["ust_yield"] = fetch_ust_yield()
    return data


def main():
    pretty = "--pretty" in sys.argv
    data = collect()
    # 附加元信息
    out = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(data),
        "items": data,
    }
    if pretty:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
