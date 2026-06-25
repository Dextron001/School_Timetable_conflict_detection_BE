-- create
CREATE TABLE COURSEITEM (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  department TEXT NOT NULL,
  academic_level TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  course_code TEXT UNIQUE,
  lecturer_name TEXT,
  day_of_the_week TEXT,
  time_start TEXT,
  time_end TEXT
);

-- insert example
INSERT INTO COURSEITEM (department, academic_level, name, description, course_code, lecturer_name, day_of_the_week, time_start, time_end)
VALUES ('CSC', '300', 'Computer Architecture', '' , 'CSC301', 'Mr Olubiyi', 'Monday', '8:30', '10:00');

-- fetch 
SELECT * FROM COURSEITEM;
