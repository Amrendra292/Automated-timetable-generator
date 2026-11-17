export type Faculty = { id: number; name: string; email: string; max_daily_load: number; unavailable_slots: number[] }
export type Room = { id: number; name: string; capacity: number; room_type: 'classroom' | 'lab' }
export type StudentGroup = { id: number; name: string; size: number }
export type Course = {
  id: number; code: string; title: string; faculty_id: number; faculty_name: string;
  group_id: number; group_name: string; sessions_per_week: number; room_type: 'classroom' | 'lab'
}
export type TimeSlot = { id: number; day: string; start_time: string; end_time: string; slot_order: number }
export type TimetableEntry = {
  id: number; course_id: number; course_code: string; course_title: string; faculty_id: number;
  faculty_name: string; group_id: number; group_name: string; room_id: number; room_name: string;
  slot_id: number; day: string; start_time: string; end_time: string; slot_order: number; room_type: string
}
export type Stats = {
  courses: number; faculty: number; rooms: number; groups: number;
  scheduled_sessions: number; weekly_sessions_required: number
}


export type OptimizationProfile = 'balanced' | 'student_first' | 'resource_saver'
export type QualityRecommendation = { title: string; detail: string; priority: string }
export type QualityReport = {
  generated: boolean; optimization_profile: OptimizationProfile; profile_label: string;
  sessions_scheduled: number; quality_score: number; hard_conflicts: number;
  compactness_score: number; average_idle_gaps_per_group_day: number; average_campus_days_per_group: number; campus_day_score: number;
  seat_utilization_pct: number; weekday_load_balance_score: number;
  daily_session_load: Record<string, number>; recommendations: QualityRecommendation[]; score_method: string
}
