from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Student Performance Report", 0, 1, "C")
        self.ln(10)

    def chapter_title(self, title):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, title, 0, 1, "L")
        self.ln(4)

    def chapter_body(self, body):
        self.set_font("Arial", "", 12)
        self.multi_cell(0, 10, body)
        self.ln()

    def add_section(self, title, content):
        if content and content.strip():
            self.chapter_title(title)
            self.chapter_body(content)

def generate_report(teacher_state, student_name, subject, topic, output_filename="student_report.pdf"):
    """
    Generates a PDF report of the student's performance.

    Args:
        teacher_state (dict): The teacher's state dictionary.
        student_name (str): The name of the student.
        subject (str): The subject of the lesson.
        topic (str): The topic of the lesson.
        output_filename (str): The name of the output PDF file.
    """
    pdf = PDF()
    pdf.add_page()

    # Basic Information
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, f"Lesson: {subject} - {topic}", 0, 1, "C")
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Student: {student_name}", 0, 1, "C")
    pdf.ln(10)

    # Focal Points
    focal_points = teacher_state.get("focal_points", [])
    if focal_points:
        pdf.add_section("Key Concepts Covered:", "- " + "\n- ".join(focal_points))

    # Performance on Activities
    activity_feedback_content = []
    for i, focal_point in enumerate(focal_points):
        quiz_feedback_key = f"quiz_{i}_feedback"
        ct_feedback_key = f"critical_thinking_{i}_feedback"
        
        feedback_str = f"Feedback for '{focal_point}':\n"
        found_feedback = False

        if quiz_feedback_key in teacher_state:
            feedback_str += f"  Quiz: {teacher_state[quiz_feedback_key]}\n"
            found_feedback = True
        
        if ct_feedback_key in teacher_state:
            feedback_str += f"  Critical Thinking: {teacher_state[ct_feedback_key]}\n"
            found_feedback = True
        
        if found_feedback:
            activity_feedback_content.append(feedback_str)
        else:
            activity_feedback_content.append(f"No specific activity feedback recorded for '{focal_point}'.\n")
            
    if activity_feedback_content:
        pdf.add_section("Performance on Lesson Activities:", "\n".join(activity_feedback_content))

    # Final Test Feedback
    final_test_feedback = teacher_state.get("final_test_feedback")
    if final_test_feedback:
        pdf.add_section("Final Test Summary & Feedback:", final_test_feedback)
    else:
        pdf.add_section("Final Test Summary & Feedback:", "No final test feedback recorded.")

    try:
        pdf.output(output_filename, "F")
        print(f"Report generated: {output_filename}")
    except Exception as e:
        print(f"Error generating PDF: {e}")
        print("Please ensure the output directory is writable and the filename is valid.")

if __name__ == '__main__':
    # Example Usage (for testing report_generator.py directly)
    sample_teacher_state = {
        "focal_points": ["Steam Engine Basics", "Impact on Transportation"],
        "quiz_0_feedback": "Excellent understanding of steam engine components!",
        "critical_thinking_1_feedback": "Good analysis of the societal impact, could explore economic factors more.",
        "final_test_feedback": "Overall, a strong performance. David showed good recall of key concepts and provided thoughtful answers during the final test. Keep up the great work!"
    }
    generate_report(sample_teacher_state, "David", "First Industrial Revolution", "The Invention of the Steam Engine", "sample_student_report.pdf")
