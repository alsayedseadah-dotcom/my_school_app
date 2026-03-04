import streamlit as st
import sqlite3
from gtts import gTTS
import os

# --- 1. إعداد قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('academy.db')
    c = conn.cursor()
    # جدول الدروس
    c.execute('''CREATE TABLE IF NOT EXISTS lessons 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT)''')
    # جدول الأسئلة المرتبط بالدروس
    c.execute('''CREATE TABLE IF NOT EXISTS questions 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, lesson_id INTEGER, 
                  q_text TEXT, opt1 TEXT, opt2 TEXT, opt3 TEXT, correct TEXT,
                  FOREIGN KEY(lesson_id) REFERENCES lessons(id))''')
    conn.commit()
    conn.close()

init_db()

# --- 2. إدارة حالة الجلسة (Session State) ---
# ضروري جداً لمنع تصفير النتيجة عند إعادة تحميل الصفحة
if 'student_results' not in st.session_state:
    st.session_state.student_results = {}  # لتخزين (رقم السؤال: هل الإجابة صحيحة؟)
if 'attempts_count' not in st.session_state:
    st.session_state.attempts_count = {}   # لتخزين عدد محاولات كل سؤال

# --- 3. تصميم الواجهة ---
st.set_page_config(page_title="منصتي التعليمية", page_icon="🎓")

mode = st.sidebar.radio("الوضع الحالي:", ["👨‍🏫 لوحة المعلم", "🎓 بوابة الطالب"])

# ---------------------------------------------------------
# قسم المعلم: إضافة دروس وأسئلة
# ---------------------------------------------------------
if mode == "👨‍🏫 لوحة المعلم":
    st.header("إضافة محتوى تعليمي جديد")
    
    with st.expander("➕ إضافة درس جديد", expanded=True):
        l_title = st.text_input("عنوان الدرس:")
        l_content = st.text_area("نص الدرس أو القصة:")
        num_q = st.number_input("عدد أسئلة الاختيار من متعدد:", min_value=1, max_value=10, value=1)
        
        q_list = []
        for i in range(int(num_q)):
            st.markdown(f"---")
            st.write(f"**إعداد السؤال ({i+1})**")
            qt = st.text_input(f"نص السؤال {i+1}", key=f"qt_{i}")
            c1, c2, c3 = st.columns(3)
            o1 = c1.text_input(f"خيار A", key=f"o1_{i}")
            o2 = c2.text_input(f"خيار B", key=f"o2_{i}")
            o3 = c3.text_input(f"خيار C", key=f"o3_{i}")
            correct_ans = st.selectbox(f"الإجابة الصحيحة للسؤال {i+1}", [o1, o2, o3], key=f"cor_{i}")
            q_list.append((qt, o1, o2, o3, correct_ans))

        if st.button("حفظ الدرس والأسئلة نهائياً"):
            if l_title and l_content:
                conn = sqlite3.connect('academy.db')
                cur = conn.cursor()
                cur.execute("INSERT INTO lessons (title, content) VALUES (?, ?)", (l_title, l_content))
                last_id = cur.lastrowid
                for q in q_list:
                    cur.execute("INSERT INTO questions (lesson_id, q_text, opt1, opt2, opt3, correct) VALUES (?, ?, ?, ?, ?, ?)", 
                                (last_id, q[0], q[1], q[2], q[3], q[4]))
                conn.commit()
                conn.close()
                st.success("✅ تم الحفظ بنجاح!")
            else:
                st.error("يرجى إكمال بيانات الدرس أولاً.")

# ---------------------------------------------------------
# قسم الطالب: المذاكرة والحل
# ---------------------------------------------------------
else:
    st.header("مرحباً بك في بوابة الاختبارات")
    
    # جلب الدروس من القاعدة
    conn = sqlite3.connect('academy.db')
    lessons = conn.execute("SELECT id, title, content FROM lessons").fetchall()
    conn.close()

    if not lessons:
        st.info("لا توجد دروس مضافة حالياً من قبل المعلم.")
    else:
        lesson_choice = st.selectbox("اختر الدرس الذي تريد حله:", [l[1] for l in lessons])
        
        # جلب بيانات الدرس المختار
        selected_lesson = [l for l in lessons if l[1] == lesson_choice][0]
        l_id, l_title, l_content = selected_lesson
        
        st.title(f"📖 {l_title}")
        st.write(l_content)
        
        # تحويل النص لصوت
        if st.button("🔊 استمع للنص"):
            with st.spinner("جاري معالجة الصوت..."):
                tts = gTTS(text=l_content, lang='ar')
                tts.save("lesson.mp3")
                st.audio("lesson.mp3")

        st.divider()
        st.subheader("📝 ابدأ الاختبار:")

        # جلب الأسئلة الخاصة بهذا الدرس
        conn = sqlite3.connect('academy.db')
        questions = conn.execute("SELECT id, q_text, opt1, opt2, opt3, correct FROM questions WHERE lesson_id=?", (l_id,)).fetchall()
        conn.close()

        for idx, q in enumerate(questions):
            q_id, q_txt, op1, op2, op3, correct = q
            st.write(f"**س{idx+1}: {q_txt}**")
            
            user_choice = st.radio(f"اختر الإجابة لـ س{idx+1}:", [op1, op2, op3], key=f"user_q_{q_id}")
            
            # زر التحقق لكل سؤال
            if st.button(f"تحقق من إجابة السؤال {idx+1}", key=f"btn_{q_id}"):
                # مفتاح المحاولات لهذا السؤال
                att_key = f"att_{q_id}"
                if att_key not in st.session_state.attempts_count:
                    st.session_state.attempts_count[att_key] = 0
                
                if user_choice == correct:
                    st.success("إجابة صحيحة! أحسنت يا بطل 🌟")
                    st.session_state.student_results[q_id] = True
                else:
                    st.session_state.attempts_count[att_key] += 1
                    st.session_state.student_results[q_id] = False
                    
                    if st.session_state.attempts_count[att_key] == 1:
                        st.warning("الإجابة خاطئة.. حاول مرة أخرى بتركيز!")
                    else:
                        st.error(f"خطأ للمرة الثانية. الإجابة الصحيحة هي: {correct}")

        st.divider()
        
        # زر النتيجة النهائية
        if st.button("🏁 عرض النتيجة النهائية والتقدير"):
            # نحسب فقط الأسئلة المرتبطة بالدرس الحالي والتي تم حلها صح
            current_lesson_q_ids = [q[0] for q in questions]
            final_score = sum(1 for q_id in current_lesson_q_ids if st.session_state.student_results.get(q_id) == True)
            total_q = len(questions)
            
            st.write(f"### نتيجتك هي: {final_score} من {total_q}")
            
            # التقدير
            ratio = final_score / total_q
            if ratio == 1:
                st.balloons()
                st.success("التقدير: ممتاز! أنت عبقري 🏆")
            elif ratio >= 0.75:
                st.info("التقدير: جيد جداً! عمل رائع 👍")
            elif ratio >= 0.5:
                st.warning("التقدير: جيد. يمكنك التحسن 📚")
            else:
                st.error("التقدير: ضعيف. راجع الدرس وحاول مجدداً.")