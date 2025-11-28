#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <random>
#include <algorithm>
#include <iomanip>
#include <limits>
#include <thread>
#include <chrono>

// Represents a single exam with its name and list of subjects.
struct Exam {
    std::string name;
    std::vector<std::string> subjects;
};

// Represents the configuration for a specific number of daily study slots.
struct TimeSlotConfig {
    int numberOfSlots;
    std::vector<std::string> timeStrings;
};

const std::vector<Exam> EXAMS_DB = {
    {"Class 10th Board (CBSE)", {"Mathematics", "Science", "Social Science", "English", "Hindi/Other"}},
    {"Class 12th Board (Science)", {"Physics", "Chemistry", "Mathematics", "English", "CS/Biology"}},
    {"JEE Mains", {"Physics", "Chemistry", "Mathematics"}},
    {"JEE Advanced", {"Physics", "Chemistry", "Mathematics", "Problem Solving"}},
    {"UPSC (Civil Services Prelims)", {"History", "Geography", "Polity", "Economics", "Science & Tech", "Environment", "Current Affairs"}},
    {"NEET (Medical Entrance)", {"Physics", "Chemistry", "Botany", "Zoology"}}
};

const std::vector<TimeSlotConfig> TIME_SLOTS_DB = {
    {2, {"09:00 - 11:00", "14:00 - 16:00"}},
    {3, {"08:00 - 10:00", "11:00 - 13:00", "15:00 - 17:00"}},
    {4, {"08:00 - 09:30", "10:00 - 11:30", "14:00 - 15:30", "16:00 - 17:30"}},
    {5, {"07:00 - 08:30", "09:00 - 10:30", "11:00 - 12:30", "15:00 - 16:30", "17:00 - 18:30"}}
};

const std::vector<std::string> DAYS = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"};

void clearScreen() {
#ifdef _WIN32
    (void)system("cls");
#else
    (void)system("clear");
#endif
}

void printHeader(const std::string& title) {
    std::cout << std::string(50, '=') << std::endl;
    std::cout << "| " << std::left << std::setw(46) << title << " |" << std::endl;
    std::cout << std::string(50, '=') << std::endl << std::endl;
}

std::string getUserChoice(const std::string& prompt, const std::vector<std::string>& validChoices) {
    std::string choice;
    while (true) {
        std::cout << prompt;
        std::cin >> choice;
        if (std::cin.good()) {
            bool isValid = false;
            for (const auto& valid : validChoices) {
                if (choice == valid) {
                    isValid = true;
                    break;
                }
            }
            if (isValid) {
                return choice;
            } else {
                std::cout << "Invalid choice. Please try again." << std::endl;
            }
        } else {
            std::cout << "Invalid input. Please enter a valid option." << std::endl;
            std::cin.clear();
            std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
        }
    }
}

Exam selectExam() {
    printHeader("Automated Timetable Generator");
    std::cout << "Please select the exam you are preparing for:\n\n";
    std::vector<std::string> validChoices;

    for (size_t i = 0; i < EXAMS_DB.size(); ++i) {
        std::string choiceNum = std::to_string(i + 1);
        std::cout << "  [" << choiceNum << "] " << EXAMS_DB[i].name << std::endl;
        validChoices.push_back(choiceNum);
    }

    std::string choice = getUserChoice("\nEnter your choice: ", validChoices);
    int index = std::stoi(choice) - 1;
    Exam selectedExam = EXAMS_DB[index];

    std::cout << "\n--------------------------------------------------" << std::endl;
    std::cout << "Important subjects for " << selectedExam.name << ":" << std::endl;
    for (const auto& subject : selectedExam.subjects) {
        std::cout << "  - " << subject << std::endl;
    }
    std::cout << "--------------------------------------------------" << std::endl;
    std::cout << "\nPress Enter to continue to set your preferences...";
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
    std::cin.get();

    return selectedExam;
}

void getUserPreferences(
    const std::vector<std::string>& subjects,
    std::map<std::string, int>& priorities,
    int& slotsPerDay,
    std::string& studyReason)
{
    clearScreen();
    printHeader("Set Your Preferences");

    std::cout << "What is your primary goal for this timetable?\n";
    std::cout << "  [1] Starting the course from scratch\n";
    std::cout << "  [2] Revision of the syllabus\n";
    std::string reasonChoice = getUserChoice("\nEnter your choice: ", {"1", "2"});
    studyReason = (reasonChoice == "1") ? "Starting from scratch" : "Revision";

    std::cout << "\nHow many hours can you study per day? (2-10)\n";
    std::string hoursStr = getUserChoice("Enter total hours: ", {"2","3","4","5","6","7","8","9","10"});
    int totalHours = std::stoi(hoursStr);

    if (totalHours <= 3) slotsPerDay = 2;
    else if (totalHours <= 5) slotsPerDay = 3;
    else if (totalHours <= 7) slotsPerDay = 4;
    else slotsPerDay = 5;

    std::cout << "-> Based on " << totalHours << " hours, we will schedule " << slotsPerDay << " study sessions.\n";

    std::cout << "\nRate your difficulty/priority for each subject (1=Low, 5=High):\n\n";
    std::vector<std::string> priorityChoices = {"1","2","3","4","5"};

    for (const auto& subject : subjects) {
        std::string prompt = "  - Priority for " + subject + ": ";
        std::string priorityStr = getUserChoice(prompt, priorityChoices);
        priorities[subject] = std::stoi(priorityStr);
    }
}

std::map<std::string, std::vector<std::string>> generateTimetable(
    const std::vector<std::string>& subjects,
    const std::map<std::string, int>& priorities,
    int slotsPerDay)
{
    std::cout << "\nGenerating your personalized timetable..." << std::endl;

    std::vector<std::string> weightedSubjects;
    for (const auto& subject : subjects) {
        int priority = priorities.at(subject);
        for (int i = 0; i < priority; ++i) {
            weightedSubjects.push_back(subject);
        }
    }

    std::random_device rd;
    std::mt19937 g(rd());

    int totalSlots = DAYS.size() * slotsPerDay;
    std::vector<std::string> studyPlan;

    while (studyPlan.size() < totalSlots) {
        std::shuffle(weightedSubjects.begin(), weightedSubjects.end(), g);
        studyPlan.insert(studyPlan.end(), weightedSubjects.begin(), weightedSubjects.end());
    }

    studyPlan.resize(totalSlots);
    std::shuffle(studyPlan.begin(), studyPlan.end(), g);

    std::map<std::string, std::vector<std::string>> timetable;
    auto it = studyPlan.begin();

    for (const auto& day : DAYS) {
        for (int i = 0; i < slotsPerDay; ++i) {
            timetable[day].push_back(*it);
            it++;
        }
        std::shuffle(timetable[day].begin(), timetable[day].end(), g);
    }
    return timetable;
}

void displayTimetable(const std::map<std::string, std::vector<std::string>>& timetable, int slotsPerDay) {
    clearScreen();
    printHeader("Your Personalized Study Timetable");

    std::vector<std::string> timeSlots;
    for(const auto& config : TIME_SLOTS_DB) {
        if (config.numberOfSlots == slotsPerDay) {
            timeSlots = config.timeStrings;
            break;
        }
    }

    if (timeSlots.empty()) {
        std::cerr << "Error: Could not find slot config." << std::endl;
        return;
    }

    size_t maxLen = 0;
    for (const auto& p : timetable)
        for (const auto& s : p.second)
            maxLen = std::max(maxLen, s.length());
    maxLen += 4;

    std::cout << std::left << std::setw(10) << "Day";
    for (const auto& t : timeSlots)
        std::cout << "| " << std::setw(maxLen) << t << " ";
    std::cout << "\n" << std::string(10 + (maxLen + 3) * slotsPerDay, '-') << "\n";

    for (const auto& day : DAYS) {
        std::cout << std::left << std::setw(10) << day;
        for (const auto& subject : timetable.at(day))
            std::cout << "| " << std::setw(maxLen) << subject << " ";
        std::cout << "\n";
    }

    std::cout << std::string(10 + (maxLen + 3) * slotsPerDay, '-') << "\n";
    std::cout << std::left << std::setw(10) << "Sunday" << "| Relax, Revise, Recharge! 🧘\n";
}

int main() {
    try {
        Exam selectedExam = selectExam();

        std::map<std::string, int> priorities;
        int slotsPerDay;
        std::string studyReason;

        getUserPreferences(selectedExam.subjects, priorities, slotsPerDay, studyReason);

        auto timetable = generateTimetable(selectedExam.subjects, priorities, slotsPerDay);

        displayTimetable(timetable, slotsPerDay);

    } catch (const std::exception& e) {
        std::cerr << "\nUnexpected error: " << e.what() << std::endl;
        return 1;
    } catch (...) {
        std::cerr << "\nUnknown error occurred." << std::endl;
        return 1;
    }

    return 0;
}
