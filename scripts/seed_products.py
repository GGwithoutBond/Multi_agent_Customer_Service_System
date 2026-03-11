"""
商品数据导入脚本
将模拟的商品数据嵌入到 Milvus 向量数据库，供 ProductWorker 检索使用

运行方式:
  cd agent-system
  uv run python scripts/seed_products.py
"""

import asyncio
import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.rag.indexer import KnowledgeIndexer
from src.core.logging import get_logger

logger = get_logger(__name__)


# =====================================================
# 商品数据 — 电子产品商城
# =====================================================
PRODUCTS = [
    # ── 手机 ──
    {
        "content": (
            "商品名称: iPhone 16 Pro Max\n"
            "商品ID: P001\n"
            "类别: 手机\n"
            "品牌: Apple\n"
            "价格: ¥9999\n"
            "库存: 328 件\n"
            "颜色: 沙漠钛金色、黑色钛金属、白色钛金属、原色钛金属\n"
            "存储: 256GB / 512GB / 1TB\n"
            "屏幕: 6.9英寸 Super Retina XDR OLED, 2868x1320, 120Hz ProMotion\n"
            "芯片: A18 Pro 仿生芯片\n"
            "摄像头: 4800万主摄 + 1200万超广角 + 1200万 5倍光学变焦长焦\n"
            "电池: 4685mAh, 支持MagSafe无线充电\n"
            "特点: 钛金属边框, 相机控制按钮, USB-C, 卫星SOS紧急联络\n"
            "适用人群: 追求极致拍照与性能的专业用户\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "手机", "brand": "Apple", "product_id": "P001", "price": 9999},
    },
    {
        "content": (
            "商品名称: iPhone 16\n"
            "商品ID: P002\n"
            "类别: 手机\n"
            "品牌: Apple\n"
            "价格: ¥5999\n"
            "库存: 562 件\n"
            "颜色: 黑色、白色、粉色、青色、群青色\n"
            "存储: 128GB / 256GB / 512GB\n"
            "屏幕: 6.1英寸 Super Retina XDR OLED, 2556x1179, 60Hz\n"
            "芯片: A18 仿生芯片\n"
            "摄像头: 4800万主摄 + 1200万超广角\n"
            "电池: 3561mAh\n"
            "特点: 动态岛, 相机控制按钮, USB-C, 支持Apple Intelligence\n"
            "适用人群: 日常使用和轻度影像需求用户\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "手机", "brand": "Apple", "product_id": "P002", "price": 5999},
    },
    {
        "content": (
            "商品名称: 华为 Mate 70 Pro+\n"
            "商品ID: P003\n"
            "类别: 手机\n"
            "品牌: 华为\n"
            "价格: ¥8999\n"
            "库存: 156 件\n"
            "颜色: 雅丹黑、星河银、冰晶蓝、昆仑霞光\n"
            "存储: 256GB / 512GB / 1TB\n"
            "屏幕: 6.9英寸 LTPO OLED, 2832x1316, 120Hz\n"
            "芯片: 麒麟9020\n"
            "摄像头: 5000万主摄 + 4000万超广角 + 4800万长焦 (支持10倍光变)\n"
            "电池: 5100mAh, 100W有线快充 + 50W无线快充\n"
            "特点: 鸿蒙4.0, 昆仑玻璃, 卫星通话, IP68防水\n"
            "适用人群: 华为生态用户, 商务人士\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "手机", "brand": "华为", "product_id": "P003", "price": 8999},
    },
    {
        "content": (
            "商品名称: 小米 15 Pro\n"
            "商品ID: P004\n"
            "类别: 手机\n"
            "品牌: 小米\n"
            "价格: ¥4999\n"
            "库存: 480 件\n"
            "颜色: 黑色、白色、绿色\n"
            "存储: 256GB / 512GB\n"
            "屏幕: 6.73英寸 2K LTPO AMOLED, 3200x1440, 120Hz\n"
            "芯片: 骁龙 8 至尊版\n"
            "摄像头: 5000万主摄 (索尼LYT-900) + 5000万超广角 + 5000万长焦\n"
            "电池: 5400mAh, 120W有线快充 + 50W无线快充\n"
            "特点: 徕卡影像, 陶瓷机身可选, 红外遥控\n"
            "适用人群: 性价比和旗舰性能兼顾的用户\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "手机", "brand": "小米", "product_id": "P004", "price": 4999},
    },

    # ── 笔记本电脑 ──
    {
        "content": (
            "商品名称: MacBook Pro 14英寸 M4 Pro\n"
            "商品ID: P005\n"
            "类别: 笔记本电脑\n"
            "品牌: Apple\n"
            "价格: ¥16999\n"
            "库存: 89 件\n"
            "颜色: 深空黑、银色\n"
            "配置: M4 Pro 芯片, 12核CPU + 16核GPU, 24GB 统一内存, 512GB SSD\n"
            "屏幕: 14.2英寸 Liquid Retina XDR, 3024x1964, 120Hz ProMotion\n"
            "续航: 长达17小时\n"
            "接口: 3个雷雳4(USB-C), HDMI, SD卡槽, MagSafe 3\n"
            "特点: 刘海屏设计, 六扬声器音响系统, 1080p摄像头\n"
            "适用人群: 创意工作者, 软件开发人员, 视频编辑\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "笔记本电脑", "brand": "Apple", "product_id": "P005", "price": 16999},
    },
    {
        "content": (
            "商品名称: MacBook Air 15英寸 M4\n"
            "商品ID: P006\n"
            "类别: 笔记本电脑\n"
            "品牌: Apple\n"
            "价格: ¥10999\n"
            "库存: 215 件\n"
            "颜色: 午夜色、星光色、深空灰、银色\n"
            "配置: M4 芯片, 10核CPU + 10核GPU, 16GB 统一内存, 256GB SSD\n"
            "屏幕: 15.3英寸 Liquid Retina, 2880x1864\n"
            "续航: 长达18小时\n"
            "重量: 1.51 kg\n"
            "接口: 2个USB-C (雷雳4), MagSafe, 3.5mm耳机孔\n"
            "特点: 无风扇设计, 安静运行, 支持Apple Intelligence\n"
            "适用人群: 学生, 轻办公用户, 经常出差的商旅人士\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "笔记本电脑", "brand": "Apple", "product_id": "P006", "price": 10999},
    },
    {
        "content": (
            "商品名称: ThinkPad X1 Carbon 2025\n"
            "商品ID: P007\n"
            "类别: 笔记本电脑\n"
            "品牌: 联想\n"
            "价格: ¥12999\n"
            "库存: 127 件\n"
            "颜色: 深黑色\n"
            "配置: Intel Core Ultra 7 258V, 32GB LPDDR5x, 1TB SSD\n"
            "屏幕: 14英寸 2.8K OLED, 2880x1800, 120Hz\n"
            "续航: 长达15小时\n"
            "重量: 1.09 kg\n"
            "接口: 2个雷雳4, USB-A, HDMI 2.1\n"
            "特点: 军标认证, 指纹识别, 红外人脸识别, 防泼溅键盘\n"
            "适用人群: 企业高端商务用户, IT 管理人员\n"
            "保修: 全国联保3年\n"
        ),
        "metadata": {"type": "product", "category": "笔记本电脑", "brand": "联想", "product_id": "P007", "price": 12999},
    },

    # ── 平板电脑 ──
    {
        "content": (
            "商品名称: iPad Pro 13英寸 M4\n"
            "商品ID: P008\n"
            "类别: 平板电脑\n"
            "品牌: Apple\n"
            "价格: ¥10999\n"
            "库存: 196 件\n"
            "颜色: 深空黑、银色\n"
            "配置: M4 芯片, 256GB 存储\n"
            "屏幕: 13英寸 Ultra Retina XDR (Tandem OLED), 2752x2064, 120Hz\n"
            "特点: Apple Pencil Pro 支持, 妙控键盘兼容, Face ID, 纤薄设计(5.1mm)\n"
            "摄像头: 1200万后置广角 + LiDAR\n"
            "适用人群: 创意设计师, 绘画爱好者, 影像编辑\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "平板电脑", "brand": "Apple", "product_id": "P008", "price": 10999},
    },
    {
        "content": (
            "商品名称: iPad Air 11英寸 M3\n"
            "商品ID: P009\n"
            "类别: 平板电脑\n"
            "品牌: Apple\n"
            "价格: ¥4799\n"
            "库存: 340 件\n"
            "颜色: 蓝色、紫色、星光色、深空灰\n"
            "配置: M3 芯片, 128GB 存储\n"
            "屏幕: 11英寸 Liquid Retina, 2360x1640\n"
            "特点: 支持Apple Pencil Pro, 妙控键盘兼容, USB-C\n"
            "适用人群: 学生, 轻设计需求用户\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "平板电脑", "brand": "Apple", "product_id": "P009", "price": 4799},
    },

    # ── 耳机 ──
    {
        "content": (
            "商品名称: AirPods Pro 2 (USB-C)\n"
            "商品ID: P010\n"
            "类别: 耳机\n"
            "品牌: Apple\n"
            "价格: ¥1899\n"
            "库存: 890 件\n"
            "类型: 真无线入耳式降噪耳机\n"
            "降噪: 主动降噪 (ANC), 自适应通透模式\n"
            "芯片: H2 芯片\n"
            "续航: 单次6小时, 配合充电盒总计30小时\n"
            "防水: IPX4 防汗防水\n"
            "特点: 个性化空间音频, 对话感知, 触控控制, U1超宽带精确查找\n"
            "适用人群: 通勤降噪, 运动, 日常使用\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "耳机", "brand": "Apple", "product_id": "P010", "price": 1899},
    },
    {
        "content": (
            "商品名称: AirPods Max (USB-C)\n"
            "商品ID: P011\n"
            "类别: 耳机\n"
            "品牌: Apple\n"
            "价格: ¥4399\n"
            "库存: 112 件\n"
            "类型: 头戴式降噪耳机\n"
            "降噪: 主动降噪 (ANC)\n"
            "芯片: H2 芯片\n"
            "续航: 长达20小时\n"
            "特点: 铝金属耳罩, 不锈钢头带, 数码旋钮, 空间音频\n"
            "重量: 384.8g\n"
            "适用人群: 音乐发烧友, 追求高端音质体验的用户\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "耳机", "brand": "Apple", "product_id": "P011", "price": 4399},
    },
    {
        "content": (
            "商品名称: Sony WH-1000XM5\n"
            "商品ID: P012\n"
            "类别: 耳机\n"
            "品牌: Sony\n"
            "价格: ¥2499\n"
            "库存: 267 件\n"
            "类型: 头戴式降噪耳机\n"
            "降噪: 行业领先自动降噪, 8颗麦克风\n"
            "驱动单元: 30mm\n"
            "续航: 长达30小时\n"
            "重量: 250g\n"
            "特点: LDAC 高解析度音频, 多设备连接, Speak-to-Chat, 折叠设计\n"
            "适用人群: 长途飞行, 办公降噪, 音乐爱好者\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "耳机", "brand": "Sony", "product_id": "P012", "price": 2499},
    },

    # ── 智能手表 ──
    {
        "content": (
            "商品名称: Apple Watch Ultra 2\n"
            "商品ID: P013\n"
            "类别: 智能手表\n"
            "品牌: Apple\n"
            "价格: ¥5999\n"
            "库存: 85 件\n"
            "材质: 钛金属表壳\n"
            "屏幕: 49mm, 最高3000尼特亮度\n"
            "芯片: S9 SiP\n"
            "续航: 长达36小时 (低电量模式72小时)\n"
            "防水: WR100 (100米防水), EN13319 潜水认证\n"
            "特点: 精确双频GPS, 深度计, 水温传感器, 86分贝警报器, 操作按钮\n"
            "适用人群: 户外探险者, 潜水爱好者, 极限运动员\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "智能手表", "brand": "Apple", "product_id": "P013", "price": 5999},
    },
    {
        "content": (
            "商品名称: Apple Watch Series 10\n"
            "商品ID: P014\n"
            "类别: 智能手表\n"
            "品牌: Apple\n"
            "价格: ¥2999\n"
            "库存: 450 件\n"
            "材质: 铝金属表壳\n"
            "屏幕: 46mm, 广角OLED\n"
            "芯片: S10 SiP\n"
            "续航: 长达18小时\n"
            "防水: WR50 (50米防水)\n"
            "特点: 睡眠呼吸暂停检测, 血氧, 心电图, 跌倒检测, 体温感应\n"
            "适用人群: 注重健康管理和日常的智能手表用户\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "智能手表", "brand": "Apple", "product_id": "P014", "price": 2999},
    },

    # ── 智能家居 ──
    {
        "content": (
            "商品名称: HomePod 2\n"
            "商品ID: P015\n"
            "类别: 智能音箱\n"
            "品牌: Apple\n"
            "价格: ¥2299\n"
            "库存: 178 件\n"
            "颜色: 午夜色、白色\n"
            "芯片: S7 芯片\n"
            "扬声器: 高振幅低音单元 + 5个高音单元\n"
            "特点: Siri 语音助手, 空间音频, 温湿度传感器, HomeKit 智能家居中枢, 隔空传送\n"
            "适用人群: Apple 生态家庭用户, 追求音质的智能音箱用户\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "智能音箱", "brand": "Apple", "product_id": "P015", "price": 2299},
    },

    # ── 配件 ──
    {
        "content": (
            "商品名称: Apple Pencil Pro\n"
            "商品ID: P016\n"
            "类别: 配件\n"
            "品牌: Apple\n"
            "价格: ¥999\n"
            "库存: 620 件\n"
            "兼容: iPad Pro M4, iPad Air M3\n"
            "特点: 触觉反馈, 找到功能, 旋转手势, 悬停预览, 精准低延迟\n"
            "充电方式: 磁吸无线充电 (吸附于iPad侧面)\n"
            "适用人群: 需要手写笔记或绘画的iPad用户\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "配件", "brand": "Apple", "product_id": "P016", "price": 999},
    },
    {
        "content": (
            "商品名称: MagSafe 充电器\n"
            "商品ID: P017\n"
            "类别: 配件\n"
            "品牌: Apple\n"
            "价格: ¥329\n"
            "库存: 1250 件\n"
            "功率: 最高15W MagSafe 无线充电\n"
            "兼容: iPhone 12 及以上全系列\n"
            "特点: 磁吸对准, 自动识别, 精确定位, 搭配20W充电头使用效果最佳\n"
            "适用人群: iPhone 用户\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "配件", "brand": "Apple", "product_id": "P017", "price": 329},
    },
    {
        "content": (
            "商品名称: 小米 67W GaN 充电器套装\n"
            "商品ID: P018\n"
            "类别: 配件\n"
            "品牌: 小米\n"
            "价格: ¥149\n"
            "库存: 2100 件\n"
            "功率: 67W 氮化镓快充\n"
            "接口: USB-C\n"
            "兼容: 安卓/iPhone/iPad/笔记本 多设备\n"
            "特点: 体积小巧, 多重安全防护, 折叠插脚\n"
            "适用人群: 需要一个充电器覆盖多设备的用户\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "配件", "brand": "小米", "product_id": "P018", "price": 149},
    },

    # ── 显示器 ──
    {
        "content": (
            "商品名称: Apple Studio Display\n"
            "商品ID: P019\n"
            "类别: 显示器\n"
            "品牌: Apple\n"
            "价格: ¥11499\n"
            "库存: 45 件\n"
            "屏幕: 27英寸 5K Retina, 5120x2880, 600尼特, P3广色域\n"
            "芯片: A13 仿生 (驱动摄像头和音频)\n"
            "摄像头: 1200万超广角, 支持人物居中\n"
            "扬声器: 6个扬声器 (4个低音+2个高音), 支持空间音频\n"
            "接口: 1个雷雳3 (96W PD供电), 3个USB-C\n"
            "适用人群: Mac 用户, 创意工作者, 影像后期\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "显示器", "brand": "Apple", "product_id": "P019", "price": 11499},
    },

    # ── AR/VR ──
    {
        "content": (
            "商品名称: Apple Vision Pro\n"
            "商品ID: P020\n"
            "类别: AR/VR 设备\n"
            "品牌: Apple\n"
            "价格: ¥29999\n"
            "库存: 23 件\n"
            "芯片: M2 + R1 双芯片\n"
            "显示: Micro-OLED, 每只眼睛超过2300万像素, 支持3D视频\n"
            "传感器: 12个摄像头, 5个传感器, 6个麦克风\n"
            "交互: 眼动追踪, 手势识别, 语音控制\n"
            "操作系统: visionOS 2\n"
            "特点: 空间计算, 沉浸式娱乐, 多屏多任务, 1:1 FaceTime\n"
            "续航: 外置电池包约2小时\n"
            "适用人群: 科技前沿探索者, 开发者, AR/VR 爱好者\n"
            "保修: 全国联保1年\n"
        ),
        "metadata": {"type": "product", "category": "AR/VR", "brand": "Apple", "product_id": "P020", "price": 29999},
    },
]


async def main():
    print("=" * 60)
    print("📦 商品数据导入 - 向量数据库 (Milvus)")
    print("=" * 60)
    print(f"共 {len(PRODUCTS)} 条商品数据待导入")
    print()

    indexer = KnowledgeIndexer()

    try:
        # 先清理可能残留的旧 collection (维度不匹配时需要重建)
        try:
            from pymilvus import connections, utility
            from src.core.config import get_settings
            settings = get_settings()
            connections.connect(
                alias="default",
                host=settings.MILVUS_HOST,
                port=settings.MILVUS_PORT,
            )
            collection_name = settings.MILVUS_COLLECTION
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                print(f"🗑️  已删除旧集合 '{collection_name}' (重建以匹配新维度)")
        except Exception as e:
            print(f"⚠️  清理旧集合时出错 (可忽略): {e}")

        # 重置 embedding 单例，确保使用最新配置
        import src.rag.embeddings as emb_module
        emb_module._embeddings = None

        # 重置 vector_store 实例
        indexer.vector_store._collection = None

        # 每条商品作为一个完整文档, 不做分块 (设置 chunk_size 大于内容长度)
        count = await indexer.index_documents(
            documents=PRODUCTS,
            chunk_size=2000,  # 足够大，保证每条商品信息不被切分
            chunk_overlap=0,
        )
        print(f"\n✅ 导入完成! 共索引 {count} 个文档块到 Milvus 向量数据库")
        print("现在可以通过聊天界面查询商品信息了, 例如:")
        print('  - "有什么手机推荐?"')
        print('  - "MacBook Pro 多少钱?"')
        print('  - "推荐一款降噪耳机"')
        print('  - "Apple Watch 有哪些型号?"')
        print('  - "5000 元以下有什么笔记本?"')

    except Exception as e:
        print(f"\n❌ 导入失败: {e}")
        print("请确保 Milvus 服务已启动 (默认端口 19530)")
        print("如果 Milvus 未安装, 请参考: https://milvus.io/docs/install_standalone-docker-compose.md")
        raise


if __name__ == "__main__":
    asyncio.run(main())
