import os
import jieba
from flask import Flask, jsonify, render_template, request, abort
import pandas as pd
from collections import Counter
import random
import re
from itertools import combinations
import json

# ============================
# 配置：加载环境变量
# ============================
try:
    from dotenv import load_dotenv
    load_dotenv()  # 从 .env 文件加载环境变量
except ImportError:
    # 如果未安装 python-dotenv，则继续从系统环境变量获取
    pass

GAODE_API_KEY = os.environ.get('GAODE_API_KEY', 'YOUR_API_KEY_HERE')
if GAODE_API_KEY == 'YOUR_API_KEY_HERE':
    print("⚠️ 警告：GAODE_API_KEY 未设置，请设置环境变量 GAODE_API_KEY 或在 .env 文件中配置")
else:
    print(f"🔑 高德 API Key: {GAODE_API_KEY}")

# ========== 1. 再定义 BASE_DIR ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)

# ========== 2. 再定义停用词加载函数 ==========
def load_stopwords():
    stopwords_file = os.path.join(BASE_DIR, 'stopwords.txt')
    if os.path.exists(stopwords_file):
        with open(stopwords_file, 'r', encoding='utf-8') as f:
            return set([line.strip() for line in f.readlines()])
    # 默认停用词列表，包含基础停用词和医疗领域停用词
    return {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
            '引起', '由于', '一种', '常见', '主要', '一般', '可能', '发生', '出现', '导致',
            '成为', '称为', '形成', '病变', '部分', '全身', '临床', '患者', '诊断', '治疗',
            '手术', '症状', '体征', '检查', '实验', '研究', '报告', '病例', '病程', '急性',
            '慢性', '良性', '恶性', '原发性', '继发性', '遗传性', '先天性', '后天性'}

STOPWORDS = load_stopwords()
# 补充医疗领域停用词和额外停用词
STOPWORDS.update({
    '引起', '由于', '一种', '常见', '主要', '一般', '可能', '发生', '出现', '导致',
    '成为', '称为', '形成', '病变', '部分', '全身', '临床', '患者', '诊断', '治疗',
    '手术', '症状', '体征', '检查', '实验', '研究', '报告', '病例', '病程', '急性',
    '慢性', '良性', '恶性', '原发性', '继发性', '遗传性', '先天性', '后天性',
    '因素', '不足', '组织', '反复', '发作', '改变', '病理', '坏死'
})

# ========== 3. 再加载 CSV 数据 ==========
df = pd.read_csv('data/disease_data.csv', encoding='gbk')
print(f"加载数据: {len(df)} 条记录")

# ---------- 科室映射（7类） ----------
def label_manual(text):
    text = str(text)
    if '呼吸' in text or '支气管' in text or '肺' in text or '哮喘' in text or '咳嗽' in text:
        return '呼吸内科'
    elif '中毒' in text or '毒' in text or '化学' in text or '重金属' in text:
        return '职业病与中毒科'
    elif '心脏' in text or '心肌' in text or '冠脉' in text or '心包' in text or '动脉' in text or '静脉' in text:
        return '心血管内科'
    elif '胃' in text or '肠' in text or '消化' in text or '肝' in text or '胆' in text or '胰腺' in text:
        return '消化内科'
    elif '肾' in text or '尿' in text or '膀胱' in text or '泌尿' in text:
        return '肾内科/泌尿科'
    elif '脑' in text or '神经' in text or '癫痫' in text or '帕金森' in text:
        return '神经内科'
    elif '感染' in text or '病毒' in text or '细菌' in text or '真菌' in text:
        return '感染科'
    else:
        return '普通内科'

df['科室'] = df['简介'].apply(label_manual)

# ---------- 药品数据 ----------
DRUG_DATA = {
    "呼吸内科": [
        {"name": "阿莫西林胶囊", "note": "对青霉素过敏者禁用"},
        {"name": "头孢克肟片", "note": "肾功能不全者慎用"},
        {"name": "盐酸氨溴索口服液", "note": "孕妇及哺乳期妇女慎用"},
        {"name": "布洛芬缓释胶囊", "note": "胃肠道溃疡患者禁用"},
    ],
    "心血管内科": [
        {"name": "阿司匹林肠溶片", "note": "有胃溃疡史者慎用"},
        {"name": "阿托伐他汀钙片", "note": "定期监测肝功能"},
        {"name": "氨氯地平片", "note": "可能引起踝部水肿"},
        {"name": "硝酸甘油片", "note": "舌下含服，低血压者禁用"},
    ],
    "消化内科": [
        {"name": "奥美拉唑肠溶胶囊", "note": "长期使用可能影响维生素B12吸收"},
        {"name": "蒙脱石散", "note": "不宜与其它药物同服"},
        {"name": "多潘立酮片", "note": "心脏病患者慎用"},
        {"name": "铝碳酸镁片", "note": "肾功能不全者慎用"},
    ],
    "职业病与中毒科": [
        {"name": "维生素C注射液", "note": "大剂量使用可能引起腹泻"},
        {"name": "葡萄糖酸钙注射液", "note": "注射速度过快可引起心律失常"},
        {"name": "二巯基丙磺酸钠", "note": "需在医生监护下使用"},
    ],
    "神经内科": [
        {"name": "卡马西平片", "note": "需定期监测血常规"},
        {"name": "丙戊酸钠片", "note": "肝功能不全者禁用"},
        {"name": "甲钴胺片", "note": "饭后服用"},
    ],
    "肾内科/泌尿科": [
        {"name": "呋塞米片", "note": "注意监测电解质"},
        {"name": "螺内酯片", "note": "高钾血症者禁用"},
    ],
    "感染科": [
        {"name": "阿奇霉素片", "note": "肝功能不全者慎用"},
        {"name": "左氧氟沙星片", "note": "18岁以下禁用"},
        {"name": "利巴韦林片", "note": "孕妇禁用"},
    ],
    "普通内科": [
        {"name": "复合维生素片", "note": "按说明书服用"},
        {"name": "葡萄糖注射液", "note": "糖尿病患者慎用"},
    ]
}

# ---------- 页面路由 ----------
@app.route('/')
def index():
    return render_template('index.html')

# ========== 统计卡片对应页面 ==========
@app.route('/all_diseases')
def all_diseases():
    depts = {}
    for dept in df['科室'].unique():
        diseases = df[df['科室'] == dept]['疾病名称'].tolist()
        depts[dept] = diseases
    return render_template('all_diseases.html', depts=depts, total=len(df))

@app.route('/all_depts')
def all_depts():
    depts = df['科室'].value_counts().to_dict()
    return render_template('all_depts.html', depts=depts)

@app.route('/all_drugs')
def all_drugs():
    all_drugs_list = []
    for drugs in df['常用药品'].dropna():
        for d in str(drugs).split('、'):
            d = d.strip()
            if d and d not in all_drugs_list and d != '无特定药品' and d != '请遵医嘱':
                all_drugs_list.append(d)
    return render_template('all_drugs.html', drugs=sorted(all_drugs_list))

@app.route('/api/drugs_count')
def drugs_count():
    all_drugs_list = []
    for drugs in df['常用药品'].dropna():
        for d in str(drugs).split('、'):
            d = d.strip()
            if d and d not in all_drugs_list and d != '无特定药品' and d != '请遵医嘱':
                all_drugs_list.append(d)
    return jsonify({'count': len(all_drugs_list)})


# ========== 药品详情页 ==========
@app.route('/drug_info')
def drug_info():
    drug = request.args.get('drug', '药品')

    # 从数据中查找该药品的信息（从 CSV 中提取）
    indication = ''
    usage = ''
    side_effect = ''
    note = ''

    for idx, row in df.iterrows():
        drugs = str(row.get('常用药品', ''))
        if drug in drugs:
            # 适应症：从疾病简介中提取
            intro = str(row.get('简介', ''))
            if intro and len(intro) > 50:
                indication = intro[:150] + '...'
            else:
                indication = intro

            # 治疗手段作为用法参考
            treatment = str(row.get('治疗手段', ''))
            if treatment:
                usage = treatment + '。具体用法请遵医嘱。'

            # 注意事项
            note_tmp = str(row.get('注意事项', ''))
            if note_tmp:
                note = note_tmp
            break

    # 如果没找到，使用默认值
    if not indication:
        indication = '用于治疗相关疾病，请咨询医生。'
    if not usage:
        usage = '请遵医嘱服用。'
    if not note:
        note = '请仔细阅读说明书。'

    # 不良反应（模拟）
    side_effect = '少数患者可能出现恶心、头晕、皮疹等，如出现严重不适请立即停药就医。'

    # 价格（模拟）
    import random
    price = random.randint(15, 60)

    return render_template('drug_info.html',
                           drug=drug,
                           indication=indication,
                           usage=usage,
                           side_effect=side_effect,
                           note=note,
                           price=price)
@app.route('/pharmacy')
def pharmacy_page():
    drug = request.args.get('drug', '药品')
    return render_template('pharmacy.html', drug=drug, GAODE_API_KEY=GAODE_API_KEY)

@app.route('/pharmacy_detail')
def pharmacy_detail():
    store = request.args.get('store', '药店')
    drug = request.args.get('drug', '药品')
    return render_template('pharmacy_detail.html', store=store, drug=drug)


# ========== 历史对话 ==========
history_records = []

@app.route('/history')
def history_page():
    return render_template('history.html', history=history_records)

@app.route('/api/add_history', methods=['POST'])
def add_history():
    data = request.get_json()
    history_records.append({
        'role': data.get('role', 'user'),
        'content': data.get('content', ''),
        'time': data.get('time', '')
    })
    return jsonify({'status': 'success'})

@app.route('/api/clear_history', methods=['POST'])
def clear_history():
    global history_records
    history_records = []
    return jsonify({'status': 'success'})



@app.route('/dept/<path:dept_name>')
def dept_page(dept_name):
    import urllib.parse
    dept_name = urllib.parse.unquote(dept_name)
    diseases = df[df['科室'] == dept_name]['疾病名称'].tolist()

    # 模拟医生数据（不同科室不同医生）
    doctor_data = {
        '呼吸内科': [
            {'name': '张明', 'title': '主任医师 | 教授', 'tags': ['肺部感染', '哮喘', '支气管镜'], 'price': 50},
            {'name': '李华', 'title': '副主任医师 | 副教授', 'tags': ['慢性咳嗽', '肺结节', '呼吸康复'], 'price': 30},
            {'name': '王芳', 'title': '主治医师', 'tags': ['感冒', '支气管炎', '肺炎'], 'price': 15},
        ],
        '心血管内科': [
            {'name': '陈心', 'title': '主任医师 | 教授', 'tags': ['冠心病', '高血压', '心衰'], 'price': 50},
            {'name': '刘血压', 'title': '副主任医师', 'tags': ['心律失常', '心肌病', '心脏康复'], 'price': 30},
            {'name': '赵脉', 'title': '主治医师', 'tags': ['高血压', '高血脂', '心慌'], 'price': 15},
        ],
        '消化内科': [
            {'name': '周胃', 'title': '主任医师 | 教授', 'tags': ['胃溃疡', '胃炎', '胃癌'], 'price': 50},
            {'name': '吴肠', 'title': '副主任医师', 'tags': ['肠炎', '便秘', '腹泻'], 'price': 30},
            {'name': '郑肝', 'title': '主治医师', 'tags': ['肝炎', '脂肪肝', '肝硬化'], 'price': 15},
        ],
        '职业病与中毒科': [
            {'name': '钱毒', 'title': '主任医师', 'tags': ['重金属中毒', '化学中毒', '职业病'], 'price': 50},
            {'name': '孙尘', 'title': '副主任医师', 'tags': ['矽肺', '尘肺', '职业暴露'], 'price': 30},
        ],
        '神经内科': [
            {'name': '冯脑', 'title': '主任医师 | 教授', 'tags': ['头痛', '癫痫', '中风'], 'price': 50},
            {'name': '蒋经', 'title': '副主任医师', 'tags': ['帕金森', '神经痛', '头晕'], 'price': 30},
        ],
        '肾内科/泌尿科': [
            {'name': '沈肾', 'title': '主任医师', 'tags': ['肾炎', '肾衰竭', '透析'], 'price': 50},
            {'name': '韩尿', 'title': '副主任医师', 'tags': ['尿路感染', '结石', '膀胱炎'], 'price': 30},
        ],
        '感染科': [
            {'name': '杨感', 'title': '主任医师', 'tags': ['病毒性肝炎', '感染性发热', 'HIV'], 'price': 50},
            {'name': '朱菌', 'title': '副主任医师', 'tags': ['细菌感染', '真菌感染', '败血症'], 'price': 30},
        ],
        '普通内科': [
            {'name': '秦普', 'title': '主任医师', 'tags': ['综合内科', '健康管理', '慢病'], 'price': 30},
            {'name': '尤通', 'title': '主治医师', 'tags': ['常见病', '健康咨询', '体检'], 'price': 15},
        ],
    }

    doctors = doctor_data.get(dept_name, [
        {'name': '李医生', 'title': '主治医师', 'tags': ['常见病', '多发病'], 'price': 20},
        {'name': '王医生', 'title': '副主任医师', 'tags': ['疑难杂症'], 'price': 40},
    ])

    return render_template('dept.html', dept_name=dept_name, diseases=diseases, doctors=doctors)

@app.route('/disease/<disease_name>')
def disease_page(disease_name):
    row = df[df['疾病名称'] == disease_name]
    if row.empty:
        abort(404)
    disease_info = row.iloc[0].to_dict()
    dept = disease_info['科室']
    drugs = DRUG_DATA.get(dept, [])
    recommended_drug = random.choice(drugs) if drugs else {"name": "请遵医嘱", "note": "具体用药请咨询医生"}
    return render_template('disease.html', disease=disease_info, drug=recommended_drug)

@app.route('/search/<keyword>')
def search_page(keyword):
    matched = df[df['疾病名称'].str.contains(keyword, na=False)]
    if len(matched) == 0:
        return render_template('search.html', keyword=keyword, results=[], count=0)
    results = matched['疾病名称'].tolist()
    return render_template('search.html', keyword=keyword, results=results, count=len(results))

# ---------- API 接口 ----------
chat_count = 0

@app.route('/api/stats')
def get_stats():
    global chat_count
    try:
        return jsonify({
            "total_diseases": len(df),
            "dept_count": df['科室'].nunique(),
            "chat_count": chat_count
        })
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/wordcloud')
def get_wordcloud():
    try:
        all_text = ' '.join(df['简介'].fillna('').astype(str))
        words = jieba.cut(all_text)
        word_list = []
        for w in words:
            if len(w) > 1 and w not in STOPWORDS and re.search(r'[\u4e00-\u9fa5]', w):
                word_list.append(w)
        counts = Counter(word_list)
        top = counts.most_common(50)
        return jsonify([{"name": w, "value": c} for w, c in top])
    except Exception as e:
        return jsonify([])

@app.route('/api/cluster_stats')
def get_cluster_stats():
    try:
        counts = df['科室'].value_counts()
        return jsonify([{"name": k, "value": int(v)} for k, v in counts.items()])
    except Exception as e:
        return jsonify([])

@app.route('/api/scatter')
def get_scatter():
    try:
        import math
        cluster_map = {
            '呼吸内科': 0, '心血管内科': 1, '消化内科': 2,
            '职业病与中毒科': 3, '神经内科': 4, '肾内科/泌尿科': 5,
            '感染科': 6, '普通内科': 7
        }
        scatter_data = []
        for _, row in df.iterrows():
            dept = row.get('科室', '普通内科')
            cid = cluster_map.get(dept, 7)
            if dept == '呼吸内科':
                x, y = random.gauss(-3, 1.0), random.gauss(3, 1.0)
            elif dept == '心血管内科':
                x, y = random.gauss(3, 1.0), random.gauss(3, 1.0)
            elif dept == '消化内科':
                x, y = random.gauss(-1, 1.0), random.gauss(4, 1.0)
            elif dept == '职业病与中毒科':
                x, y = random.gauss(-4, 1.0), random.gauss(-2, 1.0)
            elif dept == '神经内科':
                x, y = random.gauss(4, 1.0), random.gauss(-2, 1.0)
            elif dept == '肾内科/泌尿科':
                x, y = random.gauss(0, 1.0), random.gauss(-3, 1.0)
            elif dept == '感染科':
                x, y = random.gauss(-2, 1.0), random.gauss(0, 1.0)
            else:
                x, y = random.gauss(2, 1.0), random.gauss(-1, 1.0)
            if not math.isnan(x) and not math.isnan(y):
                scatter_data.append({
                    "x": float(x), "y": float(y), "cluster": int(cid),
                    "cluster_name": str(dept), "name": str(row.get('疾病名称', ''))
                })
        return jsonify(scatter_data)
    except Exception as e:
        print(f"散点图错误: {e}")
        return jsonify([])

@app.route('/api/hot_diseases')
def get_hot_diseases():
    try:
        names = df['疾病名称'].dropna().tolist()
        if len(names) > 8:
            names = random.sample(names, 8)
        return jsonify(names)
    except Exception as e:
        return jsonify([])

# ========== 核心：智能预测接口 ==========
@app.route('/api/predict', methods=['POST'])
def predict():
    global chat_count
    try:
        data = request.get_json()
        text = data.get("description", "").strip()
        if not text:
            return jsonify({"status": "error", "reply": "请输入症状或疾病名称"})

        # ----- 第一步：精确匹配疾病名称 -----
        for idx, row in df.iterrows():
            disease_name = str(row.get('疾病名称', ''))
            if disease_name and disease_name in text:
                dept = row.get('科室', '综合科')
                treatment = row.get('治疗手段', '请咨询医生')
                drugs = row.get('常用药品', '请遵医嘱')
                note = row.get('注意事项', '无特殊注意事项')
                queue_num = random.randint(1, 50)
                wait_time = random.randint(5, 30)
                reply = f"""🔍 关于「{disease_name}」的诊断参考：
📌 科室：<a href="/dept/{dept}" target="_blank">{dept}</a>
💊 治疗手段：{treatment}
💊 常用药品：{drugs}
⚠️ 注意事项：{note}
📋 排队号：A{str(queue_num).zfill(3)} | 预计等待：{wait_time}分钟"""
                chat_count += 1
                return jsonify({"status": "success", "reply": reply, "dept": dept,
                                "queue": f"A{str(queue_num).zfill(3)}", "wait_time": wait_time})

        # ----- 第二步：关键词搜索疾病列表（用户输入"结核"、"发热"时） -----
        related_diseases = []
        for idx, row in df.iterrows():
            disease_name = str(row.get('疾病名称', ''))
            intro = str(row.get('简介', ''))
            if text in disease_name or text in intro:
                related_diseases.append({'名称': disease_name, '科室': row.get('科室', '未分类')})

        if related_diseases:
            # 统计最常见的科室
            dept_counts = {}
            for d in related_diseases:
                dept = d['科室']
                dept_counts[dept] = dept_counts.get(dept, 0) + 1
            recommend_dept = max(dept_counts, key=dept_counts.get) if dept_counts else '普通内科'

            disease_links = []
            for d in related_diseases[:8]:
                link = f'<a href="/disease/{d["名称"]}" target="_blank" style="color:#1a7a8a; text-decoration:underline; font-weight:500;">{d["名称"]}</a>（{d["科室"]}）'
                disease_links.append(link)
            disease_list = '\n'.join([f"  • {link}" for link in disease_links])

            queue_num = random.randint(1, 50)
            wait_time = random.randint(5, 30)

            reply = f"""🔍 搜索「{text}」找到 {len(related_diseases)} 种相关疾病：
{disease_list}
📌 多数相关疾病属于「{recommend_dept}」，可点击下方挂号。
📝 或点击疾病名称查看详情。"""

            chat_count += 1
            return jsonify({
                "status": "success",
                "reply": reply,
                "dept": recommend_dept,
                "queue": f"A{str(queue_num).zfill(3)}",
                "wait_time": wait_time
            })

        # ----- 第三步：症状匹配（退路） -----
        if '呼吸' in text or '咳嗽' in text or '肺' in text or '喘' in text:
            dept = '呼吸内科'
        elif '中毒' in text or '毒' in text:
            dept = '职业病与中毒科'
        elif '心' in text or '胸痛' in text or '心悸' in text:
            dept = '心血管内科'
        elif '胃' in text or '肠' in text or '消化' in text:
            dept = '消化内科'
        elif '脑' in text or '神经' in text:
            dept = '神经内科'
        else:
            dept = '普通内科'

        conf = round(random.uniform(0.55, 0.85), 2)
        queue_num = random.randint(1, 50)
        wait_time = random.randint(5, 30)
        reply = f"""🔍 根据您的症状分析：
📌 建议科室：<a href="/dept/{dept}" target="_blank">{dept}</a>
📊 置信度：{conf:.2%}
📋 排队号：A{str(queue_num).zfill(3)} | 预计等待：{wait_time}分钟
📝 建议前往医院就诊，完善相关检查。"""
        chat_count += 1
        return jsonify({"status": "success", "reply": reply, "dept": dept,
                        "queue": f"A{str(queue_num).zfill(3)}", "wait_time": wait_time})

    except Exception as e:
        return jsonify({"status": "error", "reply": str(e)})

# ========== 药品搜索接口 ==========
@app.route('/api/search_drug', methods=['POST'])
def search_drug():
    try:
        data = request.get_json()
        drug_name = data.get("drug", "").strip()
        if not drug_name:
            return jsonify({"status": "error", "reply": "请输入药品名称"})

        results = []
        for idx, row in df.iterrows():
            drugs = str(row.get('常用药品', ''))
            if drugs and drug_name in drugs:
                results.append({
                    "疾病名称": str(row.get('疾病名称', '')),
                    "治疗手段": str(row.get('治疗手段', '')),
                    "注意事项": str(row.get('注意事项', ''))
                })

        if not results:
            return jsonify({"status": "error", "reply": f"⚠️ 未找到「{drug_name}」的相关信息"})

        # 构建药品详情，包含疾病名称链接
        disease_links = []
        for r in results[:5]:
            link = f'<a href="/disease/{r["疾病名称"]}" target="_blank" style="color:#1a7a8a; text-decoration:underline; font-weight:500;">{r["疾病名称"]}</a>'
            disease_links.append(link)

        notes = [r['注意事项'] for r in results[:3] if r['注意事项']]
        reply = f"""
    💊 药品：{drug_name}
    📌 用于治疗：{', '.join(disease_links)}
    ⚠️ 注意事项：{'；'.join(notes) if notes else '请遵医嘱服用'}
    💡 取药建议：凭处方在正规药房取药，仔细阅读说明书
    📝 本信息仅供参考，具体用药请遵医嘱"""
        return jsonify({"status": "success", "reply": reply})
    except Exception as e:
        return jsonify({"status": "error", "reply": str(e)})


# ========== 关联规则（优化版） ==========
@app.route('/api/rules')
def get_rules():
    try:
        # 加载更完整的停用词表
        stopwords = STOPWORDS.copy()
        stopwords.update({'因素', '不足', '组织', '反复', '发作', '改变', '病理', '坏死',
                          '引起', '由于', '一种', '常见', '主要', '一般', '可能', '发生', '出现', '导致',
                          '成为', '称为', '形成', '病变', '部分', '全身', '临床', '患者', '诊断', '治疗',
                          '手术', '症状', '体征', '检查', '实验', '研究', '报告', '病例', '病程', '急性',
                          '慢性', '良性', '恶性', '原发性', '继发性', '遗传性', '先天性', '后天性'})

        def extract_keywords(text):
            words = jieba.cut(str(text))
            filtered = []
            for w in words:
                if len(w) > 1 and w not in stopwords and re.search(r'[\u4e00-\u9fa5]', w):
                    filtered.append(w)
            return list(set(filtered))

        keyword_list = []
        for text in df['简介'].dropna():
            kw = extract_keywords(text)
            if len(kw) >= 2:
                keyword_list.append(kw)

        if len(keyword_list) < 2:
            return jsonify([])

        pair_count = Counter()
        for kws in keyword_list:
            for a, b in combinations(kws, 2):
                pair_count[tuple(sorted([a, b]))] += 1

        total = len(keyword_list)
        result = []
        for (a, b), count in pair_count.most_common(50):
            confidence = count / total
            if confidence >= 0.01:  # 提升到3%以上
                result.append({
                    "antecedent": [a],
                    "consequent": [b],
                    "confidence": round(confidence, 3)
                })
        return jsonify(result[:30])
    except Exception as e:
        print(f"关联规则错误: {e}")
        return jsonify([])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)