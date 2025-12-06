import json
import random
from typing import Dict, Optional


class Database:
    def __init__(self, questions_file: str = "questions.json"):
        self.questions_file = questions_file
        self.questions = []
        self.user_sessions = {}
        self.load_questions()

    def load_questions(self):
        try:
            with open(self.questions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.questions = data.get('questions', [])
                random.shuffle(self.questions)
        except FileNotFoundError:
            self.questions = []
        except json.JSONDecodeError:
            self.questions = []

    async def get_next_question(self, user_id: int) -> Optional[Dict]:
        if not self.questions:
            return None

        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = {
                'answered_ids': set(),
                'current_index': 0,
                'shuffled_questions': random.sample(self.questions, len(self.questions))
            }

        session = self.user_sessions[user_id]

        while session['current_index'] < len(session['shuffled_questions']):
            question = session['shuffled_questions'][session['current_index']]
            if str(question['id']) not in session['answered_ids']:
                session['current_question'] = question
                return question
            session['current_index'] += 1

        return None

    async def check_answer(self, user_id: int, user_answer: bool) -> Dict:
        if user_id not in self.user_sessions:
            return {"correct": False, "message": "Начните новую викторину"}

        session = self.user_sessions[user_id]
        question = session.get('current_question')

        if not question:
            return {"correct": False, "message": "Сначала получите вопрос"}

        is_correct = (user_answer == question['answer'])

        session['answered_ids'].add(str(question['id']))
        session['current_index'] += 1
        del session['current_question']

        return {
            "correct": is_correct,
            "correct_answer": question['answer'],
            "comment": question['comment'],
            "theme": question.get('theme', 'Общая история')
        }

    async def reset_session(self, user_id: int):
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]


db = Database()
