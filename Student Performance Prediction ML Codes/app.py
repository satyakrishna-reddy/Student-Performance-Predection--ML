from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)

# Load the student data and rank data
student_data_file = 'student_jee_mains_marks.xlsx'
rank_data_file = 'JEE_Mains_Rank_vs_Marks_Extended.xlsx'

df = pd.read_excel(student_data_file)
rank_df = pd.read_excel(rank_data_file)

# Global variable to hold the analyzed student's data
analyzed_student = None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    global analyzed_student

    roll_no = request.form.get('rollno').strip()

    # Find the student data by roll number
    student_data = df[df['Roll Number'].astype(str) == roll_no]
    
    if student_data.empty:
        return render_template('error.html', message=f"Student with roll number {roll_no} not found.")

    # Store the analyzed student data globally
    analyzed_student = student_data.iloc[0]

    # Get student name
    student_name = analyzed_student['Student Name']

    # Extract marks for 3 subjects across 6 weeks
    maths_marks = analyzed_student[['Week 1 Maths', 'Week 2 Maths', 'Week 3 Maths', 'Week 4 Maths', 'Week 5 Maths', 'Week 6 Maths']].values.flatten()
    physics_marks = analyzed_student[['Week 1 Physics', 'Week 2 Physics', 'Week 3 Physics', 'Week 4 Physics', 'Week 5 Physics', 'Week 6 Physics']].values.flatten()
    chemistry_marks = analyzed_student[['Week 1 Chemistry', 'Week 2 Chemistry', 'Week 3 Chemistry', 'Week 4 Chemistry', 'Week 5 Chemistry', 'Week 6 Chemistry']].values.flatten()

    # Calculate average marks for the 3 subjects
    subject_averages = {
        'Maths': round(maths_marks.mean(), 2),
        'Physics': round(physics_marks.mean(), 2),
        'Chemistry': round(chemistry_marks.mean(), 2)
    }

    # Sum of average marks for all subjects
    avg_marks = round(subject_averages['Maths'] + subject_averages['Physics'] + subject_averages['Chemistry'], 2)

    # Get expected rank based on the sum of average marks
    expected_rank = get_expected_rank(avg_marks)

    # Generate graphs for each subject
    img1 = create_graph(maths_marks, 'Maths', roll_no)
    img2 = create_graph(physics_marks, 'Physics', roll_no)
    img3 = create_graph(chemistry_marks, 'Chemistry', roll_no)

    # Generate overall performance graph (average of 3 subjects)
    overall_marks = (maths_marks + physics_marks + chemistry_marks) / 3
    overall_avg = create_graph(overall_marks, 'Overall Performance', roll_no)

    return render_template('result.html', 
                           name=student_name, 
                           avg_marks=avg_marks, 
                           subject_averages=subject_averages,
                           img1=img1, 
                           img2=img2, 
                           img3=img3, 
                           overall_avg=overall_avg,
                           expected_rank=expected_rank,
                           roll_no=roll_no)

@app.route('/set_target', methods=['GET', 'POST'])
def set_target():
    global analyzed_student

    if analyzed_student is None:
        return redirect(url_for('home'))

    current_performance = None
    target_rank = None
    error_message = None
    required_total_marks = None
    required_maths_marks = None
    required_physics_marks = None
    required_chemistry_marks = None

    # Automatically use the analyzed student's data
    roll_no = analyzed_student['Roll Number']
    current_performance = get_current_performance(roll_no)

    if request.method == 'POST':
        try:
            target_rank = int(request.form['target_rank'])

            if not current_performance:
                error_message = "No performance data found."
            else:
                # Calculate required marks based on target rank
                required_total_marks, required_maths_marks, required_physics_marks, required_chemistry_marks = calculate_target_marks(target_rank)

        except ValueError:
            error_message = "Invalid input. Please enter a valid rank."

    return render_template('set_target.html', 
                           current_performance=current_performance, 
                           target_rank=target_rank, 
                           error_message=error_message,
                           required_total_marks=required_total_marks,
                           required_maths_marks=required_maths_marks,
                           required_physics_marks=required_physics_marks,
                           required_chemistry_marks=required_chemistry_marks)

@app.route('/generate_schedule', methods=['POST'])
def generate_schedule():
    weeks = request.form.get('weeks')

    if weeks == '4':
        return render_template('4week.html')
    elif weeks == '8':
        return render_template('8week.html')
    elif weeks == '12':
        return render_template('12week.html')
    else:
        return redirect(url_for('set_target'))

# New route for mock test
@app.route('/mocktest')
def mock_test():
    return render_template('mocktest.html')

def create_graph(marks, subject_name, roll_no):
    plt.figure(figsize=(5, 4))
    plt.plot(marks, marker='o', color='#FFD700', label=subject_name)
    plt.title(f'{subject_name} Marks Over 6 Weeks')
    plt.xlabel('Weeks')
    plt.ylabel('Marks')
    plt.xticks(range(6), [f'Week {i+1}' for i in range(6)])
    plt.grid(True)
    plt.legend()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    
    image_png = buffer.getvalue()
    buffer.close()
    
    img_str = base64.b64encode(image_png).decode('utf-8')
    plt.close()
    return "data:image/png;base64," + img_str

def get_expected_rank(avg_marks):
    rank_row = rank_df.loc[rank_df['Total_Marks'] <= avg_marks].sort_values(by='Total_Marks', ascending=False).head(1)

    if not rank_row.empty:
        return int(rank_row['Rank'].values[0])
    else:
        return "Rank not available for this marks range"

def get_current_performance(roll_no):
    # Find the student data by roll number
    student_data = df[df['Roll Number'].astype(str) == str(roll_no)]
    
    if student_data.empty:
        return None

    # Calculate the average marks for Maths, Physics, and Chemistry over six weeks
    avg_maths = student_data[['Week 1 Maths', 'Week 2 Maths', 'Week 3 Maths', 'Week 4 Maths', 'Week 5 Maths', 'Week 6 Maths']].mean(axis=1).values[0]
    avg_physics = student_data[['Week 1 Physics', 'Week 2 Physics', 'Week 3 Physics', 'Week 4 Physics', 'Week 5 Physics', 'Week 6 Physics']].mean(axis=1).values[0]
    avg_chemistry = student_data[['Week 1 Chemistry', 'Week 2 Chemistry', 'Week 3 Chemistry', 'Week 4 Chemistry', 'Week 5 Chemistry', 'Week 6 Chemistry']].mean(axis=1).values[0]

    # Calculate the sum of the averages of all 3 subjects
    avg_total_marks = avg_maths + avg_physics + avg_chemistry

    # Get the expected rank based on the total average marks
    expected_rank = get_expected_rank(avg_total_marks)

    subject_averages = {
        'Maths': round(avg_maths, 2),
        'Physics': round(avg_physics, 2),
        'Chemistry': round(avg_chemistry, 2)
    }

    return {
        'avg_marks': avg_total_marks,
        'expected_rank': expected_rank,
        'subject_averages': subject_averages
    }

def calculate_target_marks(target_rank):
    # Retrieve the row corresponding to the target rank from the rank_df dataframe
    rank_row = rank_df[rank_df['Rank'] == target_rank]

    if rank_row.empty:
        return None, None, None, None

    total_marks_required = rank_row['Total_Marks'].values[0]
    required_maths = rank_row['Math_Marks'].values[0]  # Adjusted this line
    required_physics = rank_row['Physics_Marks'].values[0]  # Adjusted this line
    required_chemistry = rank_row['Chemistry_Marks'].values[0]  # Adjusted this line

    return total_marks_required, required_maths, required_physics, required_chemistry

if __name__ == '__main__':
    app.run(debug=True)
