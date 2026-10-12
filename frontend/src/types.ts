export type Difficulty = 'easy' | 'medium' | 'hard';
export type EvaluationGrade = 'weak' | 'partial' | 'correct' | 'strong';

export interface Question {
  id: string;
  category: string;
  difficulty: Difficulty | string;
  question: string;
  expected_knowledge: string[];
  file_reference?: string | null;
  concept?: string;
  concept_label?: string;
  topic?: string;
  source?: string;
}

export interface AnswerRecord {
  question_id: string;
  question: string;
  concept?: string;
  concept_label?: string;
  difficulty: string;
  answer: string;
  evaluation: EvaluationGrade | string;
  score: number;
  feedback: string;
  answered_at?: string;
}

export interface FinalReport {
  overall_score: number;
  readiness: string;
  concepts_tested: string[];
  strong_areas: string[];
  weak_areas: string[];
  mentor_note: string;
  notable_answers: AnswerRecord[];
  foundation_score?: number;
  system_understanding_score?: number;
}

export interface RepoProfile {
  full_name?: string;
  owner?: string;
  repo?: string;
  language?: string;
  description?: string;
  topics?: string[];
  readme_summary?: string;
  stars?: number;
  forks?: number;
  default_branch?: string;
  commit_hash?: string;
  detected_concepts?: string[];
  repository_url?: string;
}

export interface TechnologyMapItem {
  name: string;
  concept_key: string;
  importance: number;
  concepts: string[];
}

export interface EvaluationSession {
  id: string;
  student_id: string;
  repository_id: string;
  status: 'analysis' | 'in_progress' | 'completed' | string;
  profile: RepoProfile;
  current_question?: Question | null;
  questions: Question[];
  answers: AnswerRecord[];
  report: FinalReport | Record<string, unknown>;
}

export interface KBStatsData {
  pdf_bank?: {
    total_chunks?: number;
    files_indexed?: string[];
    topics?: Record<string, number>;
  };
  json_kb?: {
    total?: number;
    by_domain?: Record<string, number>;
    by_difficulty?: Record<string, number>;
  };
}
