from flask import Flask, render_template, request, redirect, url_for, session
import requests
import random
import json
import os


app = Flask(__name__)
app.secret_key = 'a12d345579gt68'  # Needed to store session data

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/username')
def username():
    return render_template('username.html')

@app.route('/select-category', methods=['POST'])
def select_category():
    session['username'] = request.form['username']
    return redirect(url_for('category'))



@app.route('/category')
def category():
    username = session.get('username', 'Guest')
    return render_template('category.html', username=username)

@app.route('/instructions', methods=['POST'])
def instructions():
    category = request.form['category']
    session['category'] = category

    # Optional: Convert category ID to name
    category_names = {
        "9": "General Knowledge",
        "18": "Science: Computers",
        "23": "History",
        "21": "Sports",
        "22": "Geography"
    }
    category_name = category_names.get(category, "Unknown")

    return render_template('instructions.html',
                           username=session.get('username'),
                           category_name=category_name)


@app.route('/instructions-page')
def instructions_page():
    username = session.get('username')
    category = session.get('category')
    return f"Welcome {username}, you selected category {category}. Instructions coming soon!"



@app.route('/start-quiz')
def start_quiz():
    category = session.get('category')  # set earlier
    url = f"https://opentdb.com/api.php?amount=10&category={category}&type=multiple"

    response = requests.get(url)
    data = response.json()

    if data['response_code'] != 0:
        return "Error fetching questions. Try again later.", 500

    questions = data['results']
    for q in questions:
        q['options'] = q['incorrect_answers'] + [q['correct_answer']]
        random.shuffle(q['options'])

    session['questions'] = questions
    session['question_index'] = 0
    session['user_answers'] = []

    return redirect(url_for('quiz'))

    # Show next question
   
@app.route('/quiz', methods=['GET', 'POST'])
def quiz():
    questions = session.get('questions')
    if questions is None:
        return redirect(url_for('start_quiz'))

    index = session.get('question_index', 0)

    # Handle answer from POST request
    if request.method == 'POST':
        selected = request.form.get('answer')
        correct = request.form.get('correct_answer')
        session['user_answers'].append({
            'question': questions[index]['question'],
            'correct_answer': correct,
            'user_answer': selected
        })
        index += 1
        session['question_index'] = index

    # If quiz is over
    if index >= len(questions):
        return redirect(url_for('result'))

    question = questions[index]
    return render_template('quiz.html', question=question, options=question['options'])


@app.route('/submit-quiz', methods=['POST'])
def submit_quiz():
    user_answers = request.form  # submitted answers
    questions = session.get('questions', [])

    score = 0
    review_data = []

    # Ensure questions exist
    if not questions:
        return "No questions found in session.", 400

    for q in questions:
        question_text = q['question']
        correct = q['correct_answer']
        selected = user_answers.get(question_text) 

        if selected == correct:
            score += 1 

        review_data.append({
            "question": question_text,
            "correct_answer": correct,
            "user_answer": selected or "No Answer"
        })

    # Store score and review data in session
    session['score'] = score
    session['review_data'] = review_data

    return redirect(url_for('result'))

@app.route('/result', methods=['GET'])
def result():
    review_data = session.get('user_answers', [])
    score = sum(1 for ans in review_data if ans['correct_answer'] == ans['user_answer'])
    total = len(review_data)
    username = session.get('username', 'Anonymous')

    if not session.get('score_saved'):
        leaderboard_file = 'score.json'
        new_entry = {"username": username, "score": score}

        if os.path.exists(leaderboard_file):
            try:
                with open(leaderboard_file, 'r') as f:
                    scores = json.load(f)
            except json.JSONDecodeError:
                scores = []
        else:
            scores = []

        scores.append(new_entry)
        scores = scores[-10:]  # Keep only last 10 scores

        with open(leaderboard_file, 'w') as f:
            json.dump(scores, f, indent=4)

        session['score_saved'] = True

    return render_template('result.html', score=score, total=total, username=username, review_data=review_data)

@app.route('/leaderboard')
def leaderboard():
    with open('score.json', 'r') as f:
        scores = json.load(f)

    # Sort by score descending
    sorted_scores = sorted(scores, key=lambda x: x['score'], reverse=True)
    return render_template('leaderboard.html', scores=sorted_scores)

if __name__ == '__main__':
    app.run(debug=True)
