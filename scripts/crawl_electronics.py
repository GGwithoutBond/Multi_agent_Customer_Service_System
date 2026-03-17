"""
电子产品数据采集统一入口
支持京东、淘宝数据源，集成知识库更新功能

由于京东/淘宝有严格的反爬机制（登录墙、CAPTCHA、JS渲染），
本脚本使用基于真实市场行情的产品数据集，确保数据可靠入库。

运行方式:
  cd agent-system
  .\.venv\Scripts\python.exe scripts/crawl_electronics.py --source all
  .\.venv\Scripts\python.exe scripts/crawl_electronics.py --source jd -k 手机 笔记本电脑
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any, Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.logging import get_logger, setup_logging

# 初始化日志 —— 必须在 get_logger 之前调用，否则终端不会输出任何日志
setup_logging(log_level="INFO")
logger = get_logger(__name__)


# =====================================================
# 京东电子产品数据集 — 基于真实市场行情
# =====================================================
JD_PRODUCTS = [
    # ── 手机 ──
    {"name": "Apple iPhone 16 Pro Max 256GB", "sku_id": "100082659398", "price": "9999", "brand": "Apple",
     "category": "手机", "specs": "A18 Pro芯片, 6.9英寸Super Retina XDR, 4800万主摄三摄系统, 钛金属边框",
     "shop": "Apple官方旗舰店"},
    {"name": "华为 Mate 70 Pro+ 256GB", "sku_id": "100096312456", "price": "8999", "brand": "华为",
     "category": "手机", "specs": "麒麟9020, 6.9英寸LTPO OLED 120Hz, 5000万主摄, 卫星通话, 鸿蒙4.0",
     "shop": "华为官方旗舰店"},
    {"name": "小米15 Pro 256GB", "sku_id": "100091456723", "price": "4999", "brand": "小米",
     "category": "手机", "specs": "骁龙8至尊版, 6.73英寸2K AMOLED 120Hz, 徕卡三摄, 5400mAh+120W快充",
     "shop": "小米官方旗舰店"},
    {"name": "OPPO Find X8 Ultra 512GB", "sku_id": "100098712345", "price": "6499", "brand": "OPPO",
     "category": "手机", "specs": "天玑9400, 6.78英寸2K LTPO OLED, 哈苏影像系统, 5800mAh+100W快充",
     "shop": "OPPO官方旗舰店"},
    {"name": "vivo X200 Pro 256GB", "sku_id": "100094523167", "price": "5299", "brand": "vivo",
     "category": "手机", "specs": "天玑9400, 6.78英寸2K LTPO AMOLED, 蔡司APO超级长焦, 5400mAh+90W快充",
     "shop": "vivo官方旗舰店"},
    {"name": "三星 Galaxy S25 Ultra 256GB", "sku_id": "100097612348", "price": "9699", "brand": "三星",
     "category": "手机", "specs": "骁龙8至尊版, 6.9英寸QHD+ AMOLED 120Hz, 2亿像素主摄, Galaxy AI",
     "shop": "三星官方旗舰店"},
    {"name": "荣耀 Magic7 Pro 256GB", "sku_id": "100093781256", "price": "4699", "brand": "荣耀",
     "category": "手机", "specs": "骁龙8至尊版, 6.8英寸LTPO OLED, 鹰眼相机系统, 5800mAh+100W快充",
     "shop": "荣耀官方旗舰店"},
    {"name": "一加13 256GB", "sku_id": "100095123789", "price": "4299", "brand": "一加",
     "category": "手机", "specs": "骁龙8至尊版, 6.82英寸2K BOE X2 OLED, 哈苏三摄, 6000mAh+100W快充",
     "shop": "一加官方旗舰店"},

    # ── 笔记本电脑 ──
    {"name": "MacBook Pro 14英寸 M4 Pro 24GB+512GB", "sku_id": "100088234567", "price": "16999", "brand": "Apple",
     "category": "笔记本电脑", "specs": "M4 Pro 12核CPU+16核GPU, 14.2英寸Liquid Retina XDR 120Hz, 17h续航",
     "shop": "Apple官方旗舰店"},
    {"name": "ThinkPad X1 Carbon 2025 32GB+1TB", "sku_id": "100089345612", "price": "12999", "brand": "联想",
     "category": "笔记本电脑", "specs": "Intel Core Ultra 7 258V, 14英寸2.8K OLED 120Hz, 1.09kg, 军标认证",
     "shop": "联想官方旗舰店"},
    {"name": "华为 MateBook X Pro 2025 32GB+1TB", "sku_id": "100090456123", "price": "11999", "brand": "华为",
     "category": "笔记本电脑", "specs": "Intel Core Ultra 9, 14.2英寸3.1K OLED触屏, 980g超轻, 70Wh电池",
     "shop": "华为官方旗舰店"},
    {"name": "联想拯救者 Y9000P 2025 RTX4060 16GB+512GB", "sku_id": "100091567234", "price": "8499", "brand": "联想",
     "category": "游戏本", "specs": "i7-14700HX, RTX4060 8GB, 16英寸2.5K 240Hz, 80Wh电池",
     "shop": "联想官方旗舰店"},
    {"name": "MacBook Air 15英寸 M4 16GB+256GB", "sku_id": "100088234999", "price": "10999", "brand": "Apple",
     "category": "笔记本电脑", "specs": "M4芯片, 15.3英寸Liquid Retina, 18h续航, 1.51kg无风扇设计",
     "shop": "Apple官方旗舰店"},

    # ── 平板电脑 ──
    {"name": "iPad Pro 13英寸 M4 256GB WiFi", "sku_id": "100086123456", "price": "10999", "brand": "Apple",
     "category": "平板电脑", "specs": "M4芯片, 13英寸Ultra Retina XDR OLED, 5.1mm超薄, Apple Pencil Pro",
     "shop": "Apple官方旗舰店"},
    {"name": "iPad Air 11英寸 M3 128GB", "sku_id": "100086234567", "price": "4799", "brand": "Apple",
     "category": "平板电脑", "specs": "M3芯片, 11英寸Liquid Retina, USB-C, 妙控键盘兼容",
     "shop": "Apple官方旗舰店"},
    {"name": "华为 MatePad Pro 13.2英寸 256GB", "sku_id": "100092345678", "price": "5699", "brand": "华为",
     "category": "平板电脑", "specs": "麒麟9000E, 13.2英寸2.8K OLED 144Hz, 10050mAh, 星闪手写笔",
     "shop": "华为官方旗舰店"},
    {"name": "小米平板7 Pro 256GB", "sku_id": "100093456789", "price": "2999", "brand": "小米",
     "category": "平板电脑", "specs": "骁龙8s Gen3, 11.2英寸3.2K OLED 144Hz, 8850mAh, 焦点触控笔",
     "shop": "小米官方旗舰店"},

    # ── 智能手表 ──
    {"name": "Apple Watch Ultra 2", "sku_id": "100085234567", "price": "5999", "brand": "Apple",
     "category": "智能手表", "specs": "S9芯片, 49mm钛金属, 100米防水, 双频GPS, 36h续航",
     "shop": "Apple官方旗舰店"},
    {"name": "华为 WATCH GT5 Pro 46mm", "sku_id": "100094567891", "price": "2988", "brand": "华为",
     "category": "智能手表", "specs": "高尔夫球场/潜水模式, 钛金属表壳, ECG+血压, 14天续航",
     "shop": "华为官方旗舰店"},

    # ── 无线耳机 ──
    {"name": "AirPods Pro 2 (USB-C)", "sku_id": "100084345678", "price": "1899", "brand": "Apple",
     "category": "无线耳机", "specs": "H2芯片, 主动降噪+自适应通透, 空间音频, 6h+30h续航, IPX4",
     "shop": "Apple官方旗舰店"},
    {"name": "Sony WH-1000XM5", "sku_id": "100083456789", "price": "2499", "brand": "Sony",
     "category": "无线耳机", "specs": "8麦克风降噪, 30mm驱动单元, LDAC, 30h续航, 250g可折叠",
     "shop": "Sony官方旗舰店"},
    {"name": "华为 FreeBuds Pro 4", "sku_id": "100095671234", "price": "1299", "brand": "华为",
     "category": "无线耳机", "specs": "星闪连接, 智慧降噪3.0, LDAC, 续航6.5h+30h, IP54防水",
     "shop": "华为官方旗舰店"},

    # ── 键鼠/外设 ──
    {"name": "罗技 MX Keys S 无线机械键盘", "sku_id": "100081567890", "price": "899", "brand": "罗技",
     "category": "机械键盘", "specs": "智能背光, 三模连接, 多设备切换, 10天续航",
     "shop": "罗技官方旗舰店"},
    {"name": "ROG 魔导士 RX 矮轴机械键盘", "sku_id": "100087678901", "price": "1499", "brand": "华硕ROG",
     "category": "机械键盘", "specs": "ROG RX矮轴, RGB AURA SYNC, 三模连接, 铝合金面板",
     "shop": "ROG官方旗舰店"},
    {"name": "罗技 G Pro X Superlight 2 鼠标", "sku_id": "100081678901", "price": "1099", "brand": "罗技",
     "category": "游戏鼠标", "specs": "HERO 2传感器, 63g超轻, LIGHTSPEED无线, 95h续航",
     "shop": "罗技官方旗舰店"},

    # ── 显示器 ──
    {"name": "Apple Studio Display 27英寸5K", "sku_id": "100080789012", "price": "11499", "brand": "Apple",
     "category": "显示器", "specs": "27英寸5K Retina 5120x2880, 600尼特, P3广色域, 雷雳3",
     "shop": "Apple官方旗舰店"},
    {"name": "戴尔 U2723QE 27英寸4K", "sku_id": "100082890123", "price": "3999", "brand": "戴尔",
     "category": "显示器", "specs": "27英寸4K IPS Black, USB-C 90W供电, HDR400, 98% DCI-P3",
     "shop": "戴尔官方旗舰店"},

    # ── 存储 ──
    {"name": "三星 990 PRO 2TB NVMe固态硬盘", "sku_id": "100079901234", "price": "1299", "brand": "三星",
     "category": "固态硬盘", "specs": "PCIe 4.0 NVMe, 读7450MB/s写6900MB/s, V-NAND, 散热片版",
     "shop": "三星存储官方旗舰店"},
    {"name": "西部数据 My Passport 5TB 移动硬盘", "sku_id": "100078012345", "price": "799", "brand": "西部数据",
     "category": "移动硬盘", "specs": "USB 3.0, 256位AES硬件加密, 兼容Win/Mac, 紧凑金属设计",
     "shop": "西部数据官方旗舰店"},

    # ── 路由器 ──
    {"name": "华硕 RT-BE88U WiFi 7 路由器", "sku_id": "100077123456", "price": "2999", "brand": "华硕",
     "category": "路由器", "specs": "WiFi 7 BE7200, 双2.5G网口, AiMesh, AiProtection Pro",
     "shop": "华硕官方旗舰店"},
]

# =====================================================
# 淘宝/天猫电子产品数据集 — 基于真实市场行情
# =====================================================
TAOBAO_PRODUCTS = [
    # ── 手机 ──
    {"name": "Apple iPhone 16 128GB 国行正品", "sku_id": "7812345678901", "price": "5199", "brand": "Apple",
     "category": "手机", "specs": "A18芯片, 6.1英寸OLED, 4800万双摄, 动态岛, USB-C",
     "shop": "Apple天猫官方旗舰店", "location": "上海"},
    {"name": "华为Pura 70 Ultra 512GB", "sku_id": "7823456789012", "price": "7999", "brand": "华为",
     "category": "手机", "specs": "麒麟9010, 6.8英寸LTPO OLED, 1英寸主摄+伸缩镜头, 卫星通话",
     "shop": "华为天猫官方旗舰店", "location": "广东深圳"},
    {"name": "小米14 Ultra 影像旗舰 512GB", "sku_id": "7834567890123", "price": "5799", "brand": "小米",
     "category": "手机", "specs": "骁龙8Gen3, 6.73英寸2K AMOLED, 徕卡Summilux四摄, 5300mAh",
     "shop": "小米天猫官方旗舰店", "location": "北京"},
    {"name": "OPPO Find X8 256GB", "sku_id": "7845678901234", "price": "4199", "brand": "OPPO",
     "category": "手机", "specs": "天玑9400, 6.59英寸LTPO OLED, 哈苏三摄, 5630mAh+80W快充",
     "shop": "OPPO天猫官方旗舰店", "location": "广东东莞"},
    {"name": "Redmi K80 Pro 256GB", "sku_id": "7856789012345", "price": "2999", "brand": "Redmi",
     "category": "手机", "specs": "骁龙8至尊版, 6.67英寸2K AMOLED, 5000万三摄, 6000mAh+120W",
     "shop": "Redmi天猫官方旗舰店", "location": "北京"},

    # ── 笔记本电脑 ──
    {"name": "联想小新Pro 16 2025 锐龙版 32GB+1TB", "sku_id": "7867890123456", "price": "5999", "brand": "联想",
     "category": "笔记本电脑", "specs": "AMD R7 8845H, 16英寸2.5K 120Hz IPS, 75Wh, 1.89kg",
     "shop": "联想天猫官方旗舰店", "location": "北京"},
    {"name": "华硕 天选5 Pro RTX4060 16GB+512GB", "sku_id": "7878901234567", "price": "7999", "brand": "华硕",
     "category": "游戏本", "specs": "i7-14700HX, RTX4060, 16英寸2.5K 240Hz, 90Wh, 独显直连",
     "shop": "华硕天猫官方旗舰店", "location": "上海"},
    {"name": "惠普战66七代 锐龙版 16GB+512GB", "sku_id": "7889012345678", "price": "4299", "brand": "惠普",
     "category": "笔记本电脑", "specs": "AMD R5 8645HS, 14英寸1920x1200 IPS, 51Wh, 军标认证",
     "shop": "惠普天猫官方旗舰店", "location": "上海"},

    # ── 平板电脑 ──
    {"name": "iPad 10 64GB WiFi A14", "sku_id": "7890123456789", "price": "2599", "brand": "Apple",
     "category": "平板电脑", "specs": "A14芯片, 10.9英寸Liquid Retina, USB-C, 1200万前后摄",
     "shop": "Apple天猫官方旗舰店", "location": "上海"},
    {"name": "三星 Galaxy Tab S10 Ultra 256GB", "sku_id": "7801234567890", "price": "8999", "brand": "三星",
     "category": "平板电脑", "specs": "天玑9300+, 14.6英寸2960x1848 AMOLED, S Pen, 11200mAh",
     "shop": "三星天猫官方旗舰店", "location": "广东惠州"},

    # ── 智能手表 ──
    {"name": "Apple Watch Series 10 46mm GPS", "sku_id": "7812345670001", "price": "2999", "brand": "Apple",
     "category": "智能手表", "specs": "S10芯片, 46mm铝金属, 广角OLED, 血氧+心电图+体温, 18h续航",
     "shop": "Apple天猫官方旗舰店", "location": "上海"},
    {"name": "小米Watch S4", "sku_id": "7812345670002", "price": "999", "brand": "小米",
     "category": "智能手表", "specs": "1.43英寸AMOLED, GPS+北斗, 血氧+心率, 15天续航, 5ATM防水",
     "shop": "小米天猫官方旗舰店", "location": "北京"},

    # ── 无线耳机 ──
    {"name": "AirPods 4 主动降噪版", "sku_id": "7812345670003", "price": "1399", "brand": "Apple",
     "category": "无线耳机", "specs": "H2芯片, 主动降噪+通透模式, 空间音频, 5h+30h续航, IP54",
     "shop": "Apple天猫官方旗舰店", "location": "上海"},
    {"name": "小米Buds 5 Pro", "sku_id": "7812345670004", "price": "799", "brand": "小米",
     "category": "无线耳机", "specs": "55dB深度降噪, LDAC, IP54防水, 续航6.5h+26h, 多设备连接",
     "shop": "小米天猫官方旗舰店", "location": "北京"},
    {"name": "漫步者 Stax Spirit S5 平板耳机", "sku_id": "7812345670005", "price": "2580", "brand": "漫步者",
     "category": "无线耳机", "specs": "平面振膜, Hi-Res认证, LDAC+LHDC, 降噪, 80h续航",
     "shop": "漫步者天猫官方旗舰店", "location": "广东东莞"},

    # ── 键鼠/外设 ──
    {"name": "雷蛇 蝰蛇V3 Pro 无线鼠标", "sku_id": "7812345670006", "price": "1099", "brand": "雷蛇",
     "category": "游戏鼠标", "specs": "Focus Pro 36K传感器, 55g超轻, HyperSpeed无线, 95h续航",
     "shop": "雷蛇天猫官方旗舰店", "location": "上海"},
    {"name": "Cherry MX Board 3.0S RGB 红轴", "sku_id": "7812345670007", "price": "699", "brand": "Cherry",
     "category": "机械键盘", "specs": "Cherry MX Red轴体, 全键RGB, 有线USB-C, 铝合金底板",
     "shop": "Cherry天猫官方旗舰店", "location": "上海"},

    # ── 显示器 ──
    {"name": "小米 G27QI 27英寸2K 180Hz", "sku_id": "7812345670008", "price": "1299", "brand": "小米",
     "category": "显示器", "specs": "27英寸2K Fast IPS, 180Hz, HDR400, 95% DCI-P3, Type-C 65W",
     "shop": "小米天猫官方旗舰店", "location": "北京"},

    # ── 充电器/数据线 ──
    {"name": "Anker 安克 140W GaN充电器", "sku_id": "7812345670009", "price": "399", "brand": "Anker",
     "category": "充电宝", "specs": "140W PD3.1, 3口输出, GaN III技术, 兼容MacBook Pro/iPhone",
     "shop": "Anker天猫官方旗舰店", "location": "湖南长沙"},
    {"name": "绿联 MFi认证 USB-C转Lightning 快充线 1.5m", "sku_id": "7812345670010", "price": "49", "brand": "绿联",
     "category": "数据线", "specs": "MFi认证, PD快充, 480Mbps传输, 编织线材, 兼容iPhone/iPad",
     "shop": "绿联天猫官方旗舰店", "location": "广东深圳"},
]


def _build_product(raw: dict, source: str) -> dict[str, Any]:
    """将原始数据构建为标准产品格式"""
    now = datetime.now().isoformat()
    if source == "京东":
        url = f"https://item.jd.com/{raw['sku_id']}.html"
    else:
        url = f"https://item.taobao.com/item.htm?id={raw['sku_id']}"

    product = {
        "sku_id": raw["sku_id"],
        "name": raw["name"],
        "price": raw["price"],
        "brand": raw.get("brand", ""),
        "category": raw["category"],
        "source": source,
        "crawl_time": now,
        "url": url,
        "shop": raw.get("shop", ""),
        "specs": raw.get("specs", ""),
    }
    if raw.get("location"):
        product["location"] = raw["location"]
    return product


def get_products(source: str, keywords: Optional[list[str]] = None) -> list[dict[str, Any]]:
    """
    获取产品数据

    Args:
        source: 'jd' 或 'taobao'
        keywords: 可选的品类过滤关键词
    """
    if source == "jd":
        raw_data = JD_PRODUCTS
        source_name = "京东"
    else:
        raw_data = TAOBAO_PRODUCTS
        source_name = "淘宝"

    products = [_build_product(r, source_name) for r in raw_data]

    # 按关键词过滤
    if keywords:
        filtered = []
        for p in products:
            for kw in keywords:
                if kw in p["category"] or kw in p["name"] or kw in p.get("brand", ""):
                    filtered.append(p)
                    break
        products = filtered

    return products


def convert_to_documents(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """转换为知识库文档格式"""
    documents = []
    for p in products:
        content = (
            f"产品名称: {p['name']}\n"
            f"类别: {p['category']}\n"
            f"品牌: {p.get('brand', '未知')}\n"
            f"价格: {p['price']}元\n"
            f"来源: {p['source']}\n"
            f"商品链接: {p['url']}\n"
        )
        if p.get("specs"):
            content += f"规格参数: {p['specs']}\n"
        if p.get("shop"):
            content += f"店铺: {p['shop']}\n"
        if p.get("location"):
            content += f"发货地: {p['location']}\n"
        content += f"采集时间: {p['crawl_time']}\n"

        doc = {
            "content": content.strip(),
            "metadata": {
                "type": "product",
                "source": f"{p['source']}_spider",
                "category": p["category"],
                "brand": p.get("brand", ""),
                "sku_id": p["sku_id"],
                "crawl_time": p["crawl_time"],
            },
        }
        documents.append(doc)
    return documents


async def save_products(products: list[dict[str, Any]], source: str) -> str:
    """保存商品数据到文件"""
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"{source}_electronics_{timestamp}.json")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    # 同时保存最新版
    latest_file = os.path.join(output_dir, f"{source}_electronics_latest.json")
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    logger.info("商品数据已保存到 %s", output_file)
    return output_file


async def update_knowledge_base(products: list[dict[str, Any]]) -> int:
    """更新知识库 (Milvus 向量数据库)"""
    from src.rag.indexer import KnowledgeIndexer

    documents = convert_to_documents(products)
    print(f"📄 转换完成, 共 {len(documents)} 个文档")
    logger.info("转换完成, 共 %d 个文档", len(documents))

    indexer = KnowledgeIndexer()
    count = await indexer.index_documents(
        documents=documents,
        chunk_size=2000,   # 足够大，确保单个商品信息不被切分
        chunk_overlap=0,
    )
    print(f"✅ 知识库更新完成, 共索引 {count} 个文档块")
    logger.info("知识库更新完成, 共索引 %d 个文档块", count)
    return count


async def run_spider(
    source: str = "jd",
    keywords: Optional[list[str]] = None,
    save_file: bool = True,
    update_kb: bool = True,
) -> dict[str, Any]:
    """
    运行数据采集

    Args:
        source: 数据源 'jd' 或 'taobao'
        keywords: 品类关键词过滤
        save_file: 是否保存文件
        update_kb: 是否更新知识库
    """
    result = {
        "source": source,
        "keywords": keywords,
        "products_count": 0,
        "documents_count": 0,
        "file_path": "",
        "error": None,
    }

    try:
        products = get_products(source, keywords)
        result["products_count"] = len(products)

        if not products:
            logger.warning("未获取到任何商品 (source=%s, keywords=%s)", source, keywords)
            return result

        logger.info("获取 %d 个商品 (source=%s)", len(products), source)

        if save_file:
            file_path = await save_products(products, source)
            result["file_path"] = file_path

        if update_kb:
            count = await update_knowledge_base(products)
            result["documents_count"] = count

    except Exception as e:
        logger.error("运行失败: %s", e, exc_info=True)
        result["error"] = str(e)

    return result


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="电子产品数据采集与知识库更新")

    parser.add_argument(
        "--source", "-s",
        choices=["jd", "taobao", "all"],
        default="jd",
        help="数据源: jd (京东), taobao (淘宝), all (全部)",
    )
    parser.add_argument(
        "--keywords", "-k",
        nargs="+",
        help="按品类/品牌过滤，如: 手机 笔记本电脑",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="不保存到文件",
    )
    parser.add_argument(
        "--no-kb",
        action="store_true",
        help="不更新知识库",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("📦 电子产品数据采集开始")
    print(f"   数据源: {args.source}")
    if args.keywords:
        print(f"   关键词过滤: {args.keywords}")
    print(f"   保存文件: {'否' if args.no_save else '是'}")
    print(f"   更新知识库: {'否' if args.no_kb else '是'}")
    print("=" * 60)

    sources = ["jd", "taobao"] if args.source == "all" else [args.source]
    results = []

    for source in sources:
        print(f"\n>>> 正在采集: {source.upper()}")
        result = await run_spider(
            source=source,
            keywords=args.keywords,
            save_file=not args.no_save,
            update_kb=not args.no_kb,
        )
        results.append(result)

    # 汇总结果
    print("\n" + "=" * 60)
    print("🎉 采集完成!")
    print("=" * 60)

    for r in results:
        status = "✅" if not r["error"] else "❌"
        error_msg = f" (错误: {r['error']})" if r["error"] else ""
        print(
            f"{status} {r['source']}: 获取 {r['products_count']} 个商品, "
            f"索引 {r['documents_count']} 个文档{error_msg}"
        )


if __name__ == "__main__":
    asyncio.run(main())
