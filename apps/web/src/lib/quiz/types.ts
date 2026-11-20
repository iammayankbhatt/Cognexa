/** Quiz, mastery and concept-page API types (mirror apps/api/app/quiz and app/api/learn.py). */

export type QuizMode = "concept" | "adaptive" | "review" | "diagnostic" | "pretest" | "posttest";
export type FeedbackMode = "immediate" | "exam";
export type QuestionType = "mcq" | "multi_select" | "true_false" | "code_output" | "short_answer";
export type ResponseValue = string | boolean | string[] | null;

export interface AnswerView {
  question_id: string;
  response: ResponseValue;
  score?: number | null;
  is_correct?: boolean | null;
  pending?: boolean;
  feedback?: string | null;
  correct_answer?: ResponseValue;
  diagnoses_prereq?: string | null;
  diagnoses_prereq_name?: string | null;
  matched_points?: string[] | null;
  missing_points?: string[] | null;
  saved?: boolean;
}

export interface QuizQuestion {
  id: string;
  concept_id: string;
  concept_name: string | null;
  type: QuestionType;
  difficulty: number;
  prompt: string;
  code: string | null;
  language: string;
  options: { id: string; text: string }[] | null;
  answer: AnswerView | null;
  explanation?: string;
}

export interface QuizSession {
  id: string;
  mode: QuizMode;
  subject_id: string;
  concept_id: string | null;
  feedback_mode: FeedbackMode;
  started_at: string;
  deadline: string | null;
  submitted_at: string | null;
  score: number | null;
  max_score: number | null;
  pending: number;
  questions: QuizQuestion[];
  per_concept: { concept_id: string; name: string; score: number; max: number }[];
  weak_prerequisites: { concept_id: string; name: string }[];
}

export interface QuizHistoryItem {
  id: string;
  mode: QuizMode;
  concept_id: string | null;
  concept_name: string | null;
  started_at: string;
  submitted_at: string;
  score: number | null;
  max_score: number | null;
  questions: number;
}

export interface QuizHistory {
  items: QuizHistoryItem[];
  page: number;
  page_size: number;
  total: number;
}

export interface MasteryItem {
  concept_id: string;
  score: number;
  effective: number;
  band: "weak" | "developing" | "strong";
  attempts: number;
  correct: number;
  last_practiced_at: string | null;
  next_review_at: string | null;
}

export interface MasteryView {
  subject_id: string;
  bands: { weak_below: number; strong_above: number };
  items: MasteryItem[];
}

export interface ConceptLink {
  id: string;
  name: string;
  cluster: string;
  mastery: number | null;
}

export interface ConceptPage {
  id: string;
  subject_id: string;
  name: string;
  cluster: string;
  difficulty: number;
  description: string;
  aliases: string[];
  sections: { kind: string; heading: string; text: string; reviewed: boolean }[];
  prerequisites: ConceptLink[];
  leads_to: ConceptLink[];
  related: ConceptLink[];
  question_count: number;
  mastery: MasteryItem | null;
}

export interface CreateQuizBody {
  mode: QuizMode;
  concept_id?: string;
  count?: number;
  timed?: boolean;
  feedback_mode?: FeedbackMode;
  question_ids?: string[];
}
