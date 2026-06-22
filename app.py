from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import json
from werkzeug.utils import secure_filename
import calendar
from collections import defaultdict

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///school.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB для фото

# Настройки для загрузки
UPLOAD_FOLDER = 'static/stickers'
COVERS_FOLDER = 'static/covers'
ATTACHMENTS_FOLDER = 'static/attachments'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['COVERS_FOLDER'] = COVERS_FOLDER
app.config['ATTACHMENTS_FOLDER'] = ATTACHMENTS_FOLDER

# Создаём папки
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COVERS_FOLDER, exist_ok=True)
os.makedirs(ATTACHMENTS_FOLDER, exist_ok=True)
os.makedirs('templates', exist_ok=True)

db = SQLAlchemy(app)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Модель ученика
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    cover = db.Column(db.String(100), default='neutral.jpg')
    color = db.Column(db.String(20), default='yellow')
    notes = db.relationship('Note', backref='student', lazy=True, cascade="all, delete-orphan")
    stickers = db.relationship('Sticker', backref='student', lazy=True, cascade="all, delete-orphan")


# Модель заметки (УРОК)
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_done = db.Column(db.Boolean, default=False)
    font_style = db.Column(db.String(20), default='handwriting')
    template_used = db.Column(db.String(50), nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    stickers = db.relationship('Sticker', backref='note', lazy=True, cascade="all, delete-orphan")
    attachments = db.relationship('Attachment', backref='note', lazy=True, cascade="all, delete-orphan")


# Модель наклейки
class Sticker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    text = db.Column(db.String(200), nullable=True)
    is_custom = db.Column(db.Boolean, default=False)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)


# Модель вложения
class Attachment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    filepath = db.Column(db.String(300), nullable=False)
    filetype = db.Column(db.String(50), nullable=False)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)


# Создаём таблицы
with app.app_context():
    db.create_all()

# Доступные наклейки
STICKERS = [
    {'id': 'genius', 'name': '🧠 Ты гений!', 'emoji': '🧠', 'text': 'Ты гений!'},
    {'id': 'star', 'name': '⭐ Ты супер!', 'emoji': '⭐', 'text': 'Ты супер!'},
    {'id': 'heart', 'name': '❤️ Молодец!', 'emoji': '❤️', 'text': 'Молодец!'},
    {'id': 'rocket', 'name': '🚀 Ты летишь!', 'emoji': '🚀', 'text': 'Ты летишь!'},
    {'id': 'unicorn', 'name': '🦄 Ты уникален!', 'emoji': '🦄', 'text': 'Ты уникален!'},
    {'id': 'sun', 'name': '☀️ Ты светишь!', 'emoji': '☀️', 'text': 'Ты светишь!'},
    {'id': 'rainbow', 'name': '🌈 Ты яркий!', 'emoji': '🌈', 'text': 'Ты яркий!'},
    {'id': 'crown', 'name': '👑 Ты король!', 'emoji': '👑', 'text': 'Ты король!'},
    {'id': 'butterfly', 'name': '🦋 Ты красива!', 'emoji': '🦋', 'text': 'Ты красива!'},
    {'id': 'diamond', 'name': '💎 Ты бриллиант!', 'emoji': '💎', 'text': 'Ты бриллиант!'},
    {'id': 'fire', 'name': '🔥 Ты огонь!', 'emoji': '🔥', 'text': 'Ты огонь!'},
    {'id': 'muscle', 'name': '💪 Ты сильный!', 'emoji': '💪', 'text': 'Ты сильный!'},
]

# Подписи для фото-наклеек
CUSTOM_STICKER_NAMES = {
    'umnica.png': '🌟 Ты умница!',
    'molodec.png': '💪 Молодец!',
    'zvezda.png': '⭐ Ты звезда!',
    'super.png': '🔥 Ты супер!',
    'krasava.png': '🌸 Ты красава!',
    'umnik.png': '🧠 Ты умник!',
    'talant.png': '🎨 Ты талант!',
    'geroi.png': '🦸 Ты герой!',
}

# 🎨 Цвета для тетрадей
COLORS = [
    {'id': 'yellow', 'name': '☀️ Жёлтый', 'bg': '#fef9e7', 'border': '#f9e79f', 'header': '#f7dc6f'},
    {'id': 'pink', 'name': '🌸 Розовый', 'bg': '#fdedec', 'border': '#f5b7b1', 'header': '#f1948a'},
    {'id': 'blue', 'name': '💙 Голубой', 'bg': '#ebf5fb', 'border': '#aed6f1', 'header': '#85c1e9'},
    {'id': 'green', 'name': '🍀 Зелёный', 'bg': '#eafaf1', 'border': '#a9dfbf', 'header': '#82e0aa'},
    {'id': 'purple', 'name': '💜 Фиолетовый', 'bg': '#f4ecf7', 'border': '#d7bde2', 'header': '#c39bd3'},
    {'id': 'orange', 'name': '🍊 Оранжевый', 'bg': '#fef9e7', 'border': '#f9e79f', 'header': '#f7dc6f'},
]

# ✍️ Стили шрифтов
FONT_STYLES = [
    {'id': 'handwriting', 'name': '✍️ Рукописный', 'css': "'Comic Sans MS', 'Segoe Script', cursive"},
    {'id': 'print', 'name': '📝 Печатный', 'css': "'Arial', 'Helvetica', sans-serif"},
    {'id': 'elegant', 'name': '✨ Элегантный', 'css': "'Georgia', 'Times New Roman', serif"},
    {'id': 'childish', 'name': '🧒 Детский', 'css': "'Comic Sans MS', 'Chalkboard SE', cursive"},
    {'id': 'minimal', 'name': '⬜ Минимальный', 'css': "'Verdana', 'Tahoma', sans-serif"},
]

# 📝 Шаблоны записей
NOTE_TEMPLATES = [
    {
        'id': 'standard',
        'name': '📋 Стандартный',
        'fields': ['date', 'topic', 'content', 'homework', 'rating']
    },
    {
        'id': 'lesson_plan',
        'name': '📚 План урока',
        'fields': ['date', 'topic', 'goal', 'materials', 'content', 'homework']
    },
    {
        'id': 'quick_note',
        'name': '⚡ Быстрая запись',
        'fields': ['date', 'topic', 'content']
    },
    {
        'id': 'feedback',
        'name': '💬 Обратная связь',
        'fields': ['date', 'topic', 'strengths', 'improvements', 'recommendations']
    },
]


def get_all_stickers():
    stickers = STICKERS.copy()
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            if allowed_file(filename):
                custom_text = CUSTOM_STICKER_NAMES.get(filename, '📸 Фото')
                stickers.append({
                    'id': f'custom_{filename}',
                    'name': f'📸 {filename}',
                    'emoji': '',
                    'text': custom_text,
                    'image_file': filename,
                    'is_custom': True
                })
    return stickers


def get_available_covers():
    covers = []
    if os.path.exists(COVERS_FOLDER):
        for filename in os.listdir(COVERS_FOLDER):
            if allowed_file(filename):
                covers.append({
                    'filename': filename,
                    'path': f'/static/covers/{filename}'
                })
    if not covers:
        covers.append({
            'filename': 'default.jpg',
            'path': '/static/covers/default.jpg'
        })
    return covers


@app.context_processor
def utility_processor():
    return {
        'get_available_covers': get_available_covers,
        'get_all_stickers': get_all_stickers,
        'COLORS': COLORS,
        'FONT_STYLES': FONT_STYLES,
        'NOTE_TEMPLATES': NOTE_TEMPLATES
    }


@app.route('/')
def index():
    students = Student.query.all()
    all_stickers = get_all_stickers()
    return render_template('index.html', students=students, all_stickers=all_stickers)


@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    covers = get_available_covers()
    if request.method == 'POST':
        name = request.form['name']
        subject = request.form['subject']
        age = request.form['age']
        cover = request.form.get('cover', 'neutral.jpg')
        color = request.form.get('color', 'yellow')

        new_student = Student(name=name, subject=subject, age=age, cover=cover, color=color)
        db.session.add(new_student)
        db.session.commit()
        flash(f'✅ Ученик {name} добавлен!')
        return redirect(url_for('index'))

    return render_template('add_student.html', covers=covers, colors=COLORS)


@app.route('/student/<int:id>')
def student_detail(id):
    student = Student.query.get_or_404(id)

    search_query = request.args.get('search', '')
    notes = Note.query.filter_by(student_id=id)
    if search_query:
        notes = notes.filter(
            (Note.topic.contains(search_query)) |
            (Note.content.contains(search_query))
        )
    notes = notes.order_by(Note.date.desc()).all()

    try:
        current_month = int(request.args.get('month', datetime.now().month))
    except (ValueError, TypeError):
        current_month = datetime.now().month

    try:
        current_year = int(request.args.get('year', datetime.now().year))
    except (ValueError, TypeError):
        current_year = datetime.now().year

    calendar_data = generate_calendar(current_year, current_month, notes)

    all_stickers = get_all_stickers()
    return render_template('student_detail.html',
                           student=student,
                           notes=notes,
                           all_stickers=all_stickers,
                           search_query=search_query,
                           calendar_data=calendar_data,
                           current_month=current_month,
                           current_year=current_year)


def generate_calendar(year, month, notes):
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]

    notes_by_date = defaultdict(list)
    for note in notes:
        try:
            day, month_num, year_num = note.date.split('.')
            date_key = f"{day}.{month_num}.{year_num}"
            notes_by_date[date_key].append(note)
        except:
            pass

    return {
        'year': year,
        'month': month,
        'month_name': month_name,
        'weeks': cal,
        'notes_by_date': notes_by_date
    }


@app.route('/add_note/<int:student_id>', methods=['GET', 'POST'])
def add_note(student_id):
    student = Student.query.get_or_404(student_id)

    if request.method == 'POST':
        date = request.form['date']
        topic = request.form['topic']
        content = request.form['content']
        is_done = 'is_done' in request.form
        font_style = request.form.get('font_style', 'handwriting')
        template_used = request.form.get('template_used')

        if template_used:
            template = next((t for t in NOTE_TEMPLATES if t['id'] == template_used), None)
            if template:
                content_parts = []
                for field in template['fields']:
                    if field in request.form and request.form[field]:
                        label = {
                            'goal': '🎯 Цель урока',
                            'materials': '📚 Материалы',
                            'homework': '📝 Домашнее задание',
                            'strengths': '💪 Что получилось',
                            'improvements': '📈 Что улучшить',
                            'recommendations': '💡 Рекомендации',
                            'rating': '⭐ Оценка'
                        }.get(field, field.capitalize())
                        content_parts.append(f"**{label}:** {request.form[field]}")

                if content_parts:
                    content = '\n\n'.join(content_parts)

        new_note = Note(
            date=date,
            topic=topic,
            content=content,
            is_done=is_done,
            font_style=font_style,
            template_used=template_used,
            student_id=student.id
        )
        db.session.add(new_note)
        db.session.commit()

        if 'attachments' in request.files:
            files = request.files.getlist('attachments')
            for file in files:
                if file and file.filename:
                    if allowed_file(file.filename):
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        name, ext = os.path.splitext(filename)
                        new_filename = f'{name}_{timestamp}{ext}'
                        filepath = os.path.join(ATTACHMENTS_FOLDER, new_filename)
                        file.save(filepath)

                        attachment = Attachment(
                            filename=filename,
                            filepath=f'/static/attachments/{new_filename}',
                            filetype=ext[1:] if ext else 'file',
                            note_id=new_note.id
                        )
                        db.session.add(attachment)

        db.session.commit()
        flash('✅ Урок добавлен в тетрадь!')
        return redirect(url_for('student_detail', id=student.id))

    now = datetime.now()
    return render_template('add_note.html',
                           student=student,
                           now=now,
                           font_styles=FONT_STYLES,
                           note_templates=NOTE_TEMPLATES)


@app.route('/add_sticker/<int:note_id>', methods=['POST'])
def add_sticker_to_note(note_id):
    note = Note.query.get_or_404(note_id)
    sticker_id = request.form['sticker_id']

    all_stickers = get_all_stickers()
    selected = next((s for s in all_stickers if s['id'] == sticker_id), None)

    if selected:
        is_custom = selected.get('is_custom', False)
        if is_custom:
            image_path = f'/static/stickers/{selected["image_file"]}'
            text = selected['text']
        else:
            image_path = selected['emoji']
            text = selected['text']

        new_sticker = Sticker(
            name=sticker_id,
            image=image_path,
            text=text,
            is_custom=is_custom,
            note_id=note.id,
            student_id=note.student_id
        )
        db.session.add(new_sticker)
        db.session.commit()
        flash(f'✨ Наклейка "{text}" добавлена к уроку!')

    return redirect(url_for('student_detail', id=note.student_id))


@app.route('/delete_sticker/<int:sticker_id>')
def delete_sticker(sticker_id):
    sticker = Sticker.query.get_or_404(sticker_id)
    student_id = sticker.student_id
    db.session.delete(sticker)
    db.session.commit()
    flash('🗑️ Наклейка удалена')
    return redirect(url_for('student_detail', id=student_id))


@app.route('/delete_attachment/<int:attachment_id>')
def delete_attachment(attachment_id):
    attachment = Attachment.query.get_or_404(attachment_id)
    student_id = attachment.note.student_id
    try:
        filepath = attachment.filepath[1:]
        if os.path.exists(filepath):
            os.remove(filepath)
    except:
        pass
    db.session.delete(attachment)
    db.session.commit()
    flash('🗑️ Вложение удалено')
    return redirect(url_for('student_detail', id=student_id))


@app.route('/delete_note/<int:note_id>')
def delete_note(note_id):
    note = Note.query.get_or_404(note_id)
    student_id = note.student.id
    db.session.delete(note)
    db.session.commit()
    flash('🗑️ Урок удалён')
    return redirect(url_for('student_detail', id=student_id))


@app.route('/toggle_note/<int:note_id>')
def toggle_note(note_id):
    note = Note.query.get_or_404(note_id)
    note.is_done = not note.is_done
    db.session.commit()
    return redirect(url_for('student_detail', id=note.student.id))


@app.route('/upload_cover', methods=['POST'])
def upload_cover():
    if 'file' not in request.files:
        flash('❌ Нет файла')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('❌ Не выбрано фото')
        return redirect(url_for('index'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        new_filename = f'cover_{timestamp}{ext}'
        file.save(os.path.join(app.config['COVERS_FOLDER'], new_filename))
        flash(f'✅ Обложка "{filename}" загружена!')
    else:
        flash('❌ Неподдерживаемый формат')
    return redirect(url_for('index'))


@app.route('/upload_sticker', methods=['POST'])
def upload_sticker():
    if 'file' not in request.files:
        flash('❌ Нет файла')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('❌ Не выбрано фото')
        return redirect(url_for('index'))
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        new_filename = f'{name}_{timestamp}{ext}'
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
        flash(f'✅ Наклейка "{filename}" загружена!')
    else:
        flash('❌ Неподдерживаемый формат')
    return redirect(url_for('index'))


@app.route('/delete_cover/<filename>')
def delete_cover(filename):
    try:
        filepath = os.path.join(COVERS_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            flash('🗑️ Обложка удалена')
        else:
            flash('❌ Файл не найден')
    except Exception as e:
        flash(f'❌ Ошибка: {e}')
    return redirect(url_for('index'))


@app.route('/delete_custom_sticker/<filename>')
def delete_custom_sticker(filename):
    try:
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            flash('🗑️ Наклейка удалена')
        else:
            flash('❌ Файл не найден')
    except Exception as e:
        flash(f'❌ Ошибка: {e}')
    return redirect(url_for('index'))


@app.route('/search_notes/<int:student_id>')
def search_notes(student_id):
    query = request.args.get('q', '')
    notes = Note.query.filter_by(student_id=student_id)
    if query:
        notes = notes.filter(
            (Note.topic.contains(query)) |
            (Note.content.contains(query))
        )
    notes = notes.order_by(Note.date.desc()).all()
    results = []
    for note in notes:
        results.append({
            'id': note.id,
            'date': note.date,
            'topic': note.topic,
            'content': note.content[:100] + '...' if len(note.content) > 100 else note.content,
            'is_done': note.is_done
        })
    return jsonify(results)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)