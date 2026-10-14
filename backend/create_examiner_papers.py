import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database.session import async_session_factory
from app.models.user import User
from app.models.question_paper import QuestionPaper
from app.models.exam_section_rule import ExamSectionRule
from app.models.exam_question_rule import ExamQuestionRule
from app.models.question_option import QuestionOption
from app.models.exam import Exam

async def create_papers_for_examiner():
    target_email = "ekvtdy0791@minitts.net"
    
    async with async_session_factory() as db:
        # 1. Fetch examiner user
        res = await db.execute(select(User).where(User.email == target_email))
        examiner = res.scalar_one_or_none()
        if not examiner:
            print(f"Error: Examiner with email {target_email} not found!")
            return
        
        print(f"Found examiner: {examiner.full_name} (ID: {examiner.id}, Email: {examiner.email})")

        created_papers_info = []

        # =========================================================================
        # 1. MCQ ONLY PAPER
        # =========================================================================
        paper_mcq = QuestionPaper(
            title="Computer Science Fundamentals - MCQ Examination",
            course_name="Computer Science",
            description="Comprehensive multiple-choice assessment covering core algorithms, data structures, and computer architecture.",
            uploaded_by=examiner.id,
            mode="STRUCTURED",
            version=1,
            revision=1,
            status="READY"
        )
        db.add(paper_mcq)
        await db.flush()

        sec_mcq = ExamSectionRule(
            question_paper_id=paper_mcq.id,
            section_index=0,
            section_name="Section A - Core Multiple Choice Questions",
            section_type="MCQ",
            section_duration_minutes=20,
            navigation_policy="FREE",
            allow_return_to_previous=True,
            lock_after_timeout=False,
            randomize_questions=False,
            require_completion_before_next=False,
            section_weight=1.0,
            instructions="Select the single correct option for each question. All questions carry equal marks."
        )
        db.add(sec_mcq)
        await db.flush()

        mcq_data = [
            {
                "text": "What is the worst-case time complexity of searching an element in a balanced Binary Search Tree (AVL / Red-Black)?",
                "explanation": "Balanced BSTs maintain a height of O(log n), ensuring lookup operations take logarithmic time in the worst case.",
                "difficulty": "MEDIUM",
                "marks": 2,
                "options": [
                    ("O(1)", False),
                    ("O(log n)", True),
                    ("O(n)", False),
                    ("O(n log n)", False)
                ]
            },
            {
                "text": "Which fundamental data structure operates strictly on the Last-In, First-Out (LIFO) principle?",
                "explanation": "A Stack pushes and pops elements from the same end, following the LIFO access order.",
                "difficulty": "EASY",
                "marks": 2,
                "options": [
                    ("Queue", False),
                    ("Stack", True),
                    ("Linked List", False),
                    ("Binary Heap", False)
                ]
            },
            {
                "text": "Which HTTP status code signifies that the requested resource could not be found on the server?",
                "explanation": "HTTP 404 Not Found is returned when the origin server cannot locate a current representation for the target resource.",
                "difficulty": "EASY",
                "marks": 2,
                "options": [
                    ("200 OK", False),
                    ("401 Unauthorized", False),
                    ("403 Forbidden", False),
                    ("404 Not Found", True)
                ]
            },
            {
                "text": "In relational database design, what are the mandatory properties of a Primary Key?",
                "explanation": "A primary key column must contain unique values for every row and cannot contain NULL values.",
                "difficulty": "EASY",
                "marks": 2,
                "options": [
                    ("Must be unique and cannot contain NULL values", True),
                    ("Can contain NULL values as long as foreign keys reference it", False),
                    ("Must always be an auto-incrementing integer", False),
                    ("Must be indexed with duplicate allowed", False)
                ]
            },
            {
                "text": "Which CPU scheduling algorithm assigns a fixed time quantum to each ready process in cyclic order?",
                "explanation": "Round Robin scheduling allocates a fixed time slice (quantum) per process in circular FIFO sequence.",
                "difficulty": "MEDIUM",
                "marks": 2,
                "options": [
                    ("First-Come, First-Served (FCFS)", False),
                    ("Shortest Job First (SJF)", False),
                    ("Round Robin (RR)", True),
                    ("Priority Preemptive Scheduling", False)
                ]
            },
            {
                "text": "Which of the following is a non-volatile type of computer memory that retains data without continuous power?",
                "explanation": "Flash Memory / ROM is non-volatile and retains stored data even when electrical power is switched off.",
                "difficulty": "EASY",
                "marks": 2,
                "options": [
                    ("SRAM", False),
                    ("DRAM", False),
                    ("Flash Memory / ROM", True),
                    ("CPU L1 Cache", False)
                ]
            },
            {
                "text": "How many bits are used to represent a standard IPv4 network address?",
                "explanation": "An IPv4 address consists of 32 bits (4 octets represented in dotted decimal format).",
                "difficulty": "EASY",
                "marks": 2,
                "options": [
                    ("16 bits", False),
                    ("32 bits", True),
                    ("64 bits", False),
                    ("128 bits", False)
                ]
            },
            {
                "text": "What is the average-case time complexity of the QuickSort algorithm?",
                "explanation": "QuickSort achieves O(n log n) average time complexity through divide-and-conquer partitioning.",
                "difficulty": "MEDIUM",
                "marks": 2,
                "options": [
                    ("O(n)", False),
                    ("O(n log n)", True),
                    ("O(n^2)", False),
                    ("O(2^n)", False)
                ]
            }
        ]

        for idx, q_info in enumerate(mcq_data):
            q_rule = ExamQuestionRule(
                question_paper_id=paper_mcq.id,
                section_rule_id=sec_mcq.id,
                question_index=idx,
                question_type="MCQ",
                marks=q_info["marks"],
                is_required=True,
                question_text=q_info["text"],
                explanation=q_info["explanation"],
                difficulty=q_info["difficulty"]
            )
            db.add(q_rule)
            await db.flush()
            for opt_text, is_corr in q_info["options"]:
                db.add(QuestionOption(
                    question_rule_id=q_rule.id,
                    option_text=opt_text,
                    is_correct=is_corr
                ))

        created_papers_info.append(("MCQ Only", paper_mcq, 20, 16))

        # =========================================================================
        # 2. SUBJECTIVE ONLY PAPER
        # =========================================================================
        paper_subj = QuestionPaper(
            title="Software Engineering & Architecture - Subjective Paper",
            course_name="Software Engineering",
            description="In-depth theoretical and analytical subjective examination on software design patterns, architectural trade-offs, and distributed systems.",
            uploaded_by=examiner.id,
            mode="STRUCTURED",
            version=1,
            revision=1,
            status="READY"
        )
        db.add(paper_subj)
        await db.flush()

        sec_subj = ExamSectionRule(
            question_paper_id=paper_subj.id,
            section_index=0,
            section_name="Section A - Theoretical & Architectural Analysis",
            section_type="SUBJECTIVE",
            section_duration_minutes=45,
            navigation_policy="FREE",
            allow_return_to_previous=True,
            lock_after_timeout=False,
            randomize_questions=False,
            require_completion_before_next=False,
            section_weight=1.0,
            instructions="Provide clear, well-structured, and comprehensive technical explanations for each question."
        )
        db.add(sec_subj)
        await db.flush()

        subj_data = [
            {
                "text": "Explain the SOLID design principles in Object-Oriented Software Engineering. Provide a concrete real-world example illustrating Single Responsibility (SRP) and Dependency Inversion (DIP).",
                "difficulty": "HARD",
                "marks": 10,
                "word_limit": 600
            },
            {
                "text": "Compare and contrast Monolithic Architecture versus Microservices Architecture. Analyze their trade-offs in terms of deployment complexity, data consistency, scalability, and network latency.",
                "difficulty": "HARD",
                "marks": 10,
                "word_limit": 600
            },
            {
                "text": "Define the ACID properties of Relational Databases (Atomicity, Consistency, Isolation, Durability). How do distributed databases trade off consistency and availability under the CAP Theorem?",
                "difficulty": "MEDIUM",
                "marks": 10,
                "word_limit": 500
            },
            {
                "text": "Discuss the core stages of a modern Continuous Integration and Continuous Deployment (CI/CD) pipeline. How do automated unit, integration, and security scans ensure high deployment quality?",
                "difficulty": "MEDIUM",
                "marks": 10,
                "word_limit": 500
            },
            {
                "text": "Detail the four Coffman conditions necessary for a Deadlock to occur in Operating Systems. Explain how resource allocation graphs and Dijkstra's Banker's Algorithm prevent deadlocks.",
                "difficulty": "HARD",
                "marks": 10,
                "word_limit": 600
            }
        ]

        for idx, q_info in enumerate(subj_data):
            q_rule = ExamQuestionRule(
                question_paper_id=paper_subj.id,
                section_rule_id=sec_subj.id,
                question_index=idx,
                question_type="SUBJECTIVE",
                marks=q_info["marks"],
                is_required=True,
                question_text=q_info["text"],
                difficulty=q_info["difficulty"],
                word_limit=q_info["word_limit"]
            )
            db.add(q_rule)

        created_papers_info.append(("Subjective Only", paper_subj, 45, 50))

        # =========================================================================
        # 3. MIXED PAPER (MCQ + SUBJECTIVE)
        # =========================================================================
        paper_mixed = QuestionPaper(
            title="Database Management & Web Applications - Mixed Exam",
            course_name="Information Technology",
            description="Balanced evaluation containing both conceptual multiple-choice questions and comprehensive subjective design questions.",
            uploaded_by=examiner.id,
            mode="STRUCTURED",
            version=1,
            revision=1,
            status="READY"
        )
        db.add(paper_mixed)
        await db.flush()

        # Section 1: MCQ (15 mins)
        sec_mixed_mcq = ExamSectionRule(
            question_paper_id=paper_mixed.id,
            section_index=0,
            section_name="Section A - Objective Multiple Choice",
            section_type="MCQ",
            section_duration_minutes=15,
            navigation_policy="FREE",
            allow_return_to_previous=True,
            lock_after_timeout=False,
            randomize_questions=False,
            require_completion_before_next=False,
            section_weight=1.0,
            instructions="Attempt all multiple choice questions."
        )
        db.add(sec_mixed_mcq)
        await db.flush()

        mixed_mcq_data = [
            {
                "text": "According to HTTP specifications, which of the following request methods is guaranteed to be idempotent?",
                "explanation": "GET, PUT, and DELETE are idempotent; multiple identical requests produce the same side effect.",
                "difficulty": "MEDIUM",
                "marks": 2,
                "options": [
                    ("POST", False),
                    ("PUT", True),
                    ("PATCH", False),
                    ("CONNECT", False)
                ]
            },
            {
                "text": "In React, which built-in Hook is designed to perform asynchronous operations, subscriptions, and DOM mutations?",
                "explanation": "useEffect handles lifecycle side-effects in functional components.",
                "difficulty": "EASY",
                "marks": 2,
                "options": [
                    ("useState", False),
                    ("useMemo", False),
                    ("useEffect", True),
                    ("useRef", False)
                ]
            },
            {
                "text": "What is the primary function of a JSON Web Token (JWT) in modern web applications?",
                "explanation": "JWT securely transmits compact, digitally signed JSON claims for stateless authentication.",
                "difficulty": "EASY",
                "marks": 2,
                "options": [
                    ("To encrypt server database files", False),
                    ("To securely transmit digitally signed claims for authentication", True),
                    ("To optimize client-side CSS bundling", False),
                    ("To compile TypeScript into WebAssembly", False)
                ]
            },
            {
                "text": "In SQL, which clause is specifically used to filter records AFTER an aggregation operation (such as GROUP BY)?",
                "explanation": "HAVING filters aggregated groups, whereas WHERE filters individual rows prior to grouping.",
                "difficulty": "MEDIUM",
                "marks": 2,
                "options": [
                    ("WHERE", False),
                    ("HAVING", True),
                    ("ORDER BY", False),
                    ("GROUP FILTER", False)
                ]
            },
            {
                "text": "Which CSS layout module introduces a two-dimensional grid-based layout system with columns and rows?",
                "explanation": "CSS Grid Layout is designed specifically for 2D multi-row, multi-column web layouts.",
                "difficulty": "EASY",
                "marks": 2,
                "options": [
                    ("Flexbox", False),
                    ("Float & Clear", False),
                    ("CSS Grid", True),
                    ("Absolute Positioning", False)
                ]
            }
        ]

        for idx, q_info in enumerate(mixed_mcq_data):
            q_rule = ExamQuestionRule(
                question_paper_id=paper_mixed.id,
                section_rule_id=sec_mixed_mcq.id,
                question_index=idx,
                question_type="MCQ",
                marks=q_info["marks"],
                is_required=True,
                question_text=q_info["text"],
                explanation=q_info["explanation"],
                difficulty=q_info["difficulty"]
            )
            db.add(q_rule)
            await db.flush()
            for opt_text, is_corr in q_info["options"]:
                db.add(QuestionOption(
                    question_rule_id=q_rule.id,
                    option_text=opt_text,
                    is_correct=is_corr
                ))

        # Section 2: Subjective (30 mins)
        sec_mixed_subj = ExamSectionRule(
            question_paper_id=paper_mixed.id,
            section_index=1,
            section_name="Section B - Subjective Design & Implementation",
            section_type="SUBJECTIVE",
            section_duration_minutes=30,
            navigation_policy="FREE",
            allow_return_to_previous=True,
            lock_after_timeout=False,
            randomize_questions=False,
            require_completion_before_next=False,
            section_weight=1.0,
            instructions="Provide detailed analytical answers for the design questions below."
        )
        db.add(sec_mixed_subj)
        await db.flush()

        mixed_subj_data = [
            {
                "text": "Explain the architectural principles of RESTful APIs. Compare REST with GraphQL regarding data over-fetching, under-fetching, and schema governance.",
                "difficulty": "MEDIUM",
                "marks": 10,
                "word_limit": 500
            },
            {
                "text": "Describe how WebSockets establish persistent, bidirectional, full-duplex communication channels between client and server. When is WebSockets preferred over HTTP Long-Polling or SSE?",
                "difficulty": "MEDIUM",
                "marks": 10,
                "word_limit": 500
            },
            {
                "text": "Design a multi-tier caching architecture for a high-traffic web application using an in-memory store like Redis. Discuss Cache-Aside strategy, cache invalidation, and prevention of Cache Stampede.",
                "difficulty": "HARD",
                "marks": 10,
                "word_limit": 600
            }
        ]

        for idx, q_info in enumerate(mixed_subj_data):
            q_rule = ExamQuestionRule(
                question_paper_id=paper_mixed.id,
                section_rule_id=sec_mixed_subj.id,
                question_index=idx,
                question_type="SUBJECTIVE",
                marks=q_info["marks"],
                is_required=True,
                question_text=q_info["text"],
                difficulty=q_info["difficulty"],
                word_limit=q_info["word_limit"]
            )
            db.add(q_rule)

        created_papers_info.append(("Mixed MCQ & Subjective", paper_mixed, 45, 40))

        # =========================================================================
        # 4. SESSION BY SESSION PAPER (3 SESSIONS, EACH 5 MINUTES, TITLED "3 Sessions")
        # =========================================================================
        paper_sessions = QuestionPaper(
            title="3 Sessions",
            course_name="Artificial Intelligence & Logic",
            description="Multi-session structured assessment featuring 3 distinct 5-minute timed sessions with sequential progression and strict session locks.",
            uploaded_by=examiner.id,
            mode="STRUCTURED",
            version=1,
            revision=1,
            status="READY"
        )
        db.add(paper_sessions)
        await db.flush()

        # Session 1: AI Foundations & Search (5 mins)
        sec_sess1 = ExamSectionRule(
            question_paper_id=paper_sessions.id,
            section_index=0,
            section_name="Session 1 - AI Foundations & Search Algorithms",
            section_type="MCQ",
            section_duration_minutes=5,
            navigation_policy="SEQUENTIAL",
            allow_return_to_previous=False,
            lock_after_timeout=True,
            randomize_questions=False,
            require_completion_before_next=True,
            section_weight=1.0,
            instructions="Session 1: Time limit is strictly 5 minutes. Answers lock automatically upon transition."
        )
        db.add(sec_sess1)
        await db.flush()

        sess1_mcqs = [
            {
                "text": "Which graph traversal algorithm guarantees finding the shortest path on an unweighted state-space graph?",
                "explanation": "BFS expands nodes level by level, ensuring the shallowest (shortest) path is discovered first.",
                "difficulty": "EASY",
                "marks": 5,
                "options": [
                    ("Depth-First Search (DFS)", False),
                    ("Breadth-First Search (BFS)", True),
                    ("Depth-Limited Search", False),
                    ("Bidirectional Greedy Search", False)
                ]
            },
            {
                "text": "In the A* Search algorithm, what evaluation function f(n) determines the priority of node expansion?",
                "explanation": "f(n) = g(n) + h(n), where g(n) is the exact path cost from start and h(n) is the heuristic estimate to goal.",
                "difficulty": "MEDIUM",
                "marks": 5,
                "options": [
                    ("f(n) = g(n) - h(n)", False),
                    ("f(n) = g(n) * h(n)", False),
                    ("f(n) = g(n) + h(n)", True),
                    ("f(n) = max(g(n), h(n))", False)
                ]
            },
            {
                "text": "Which optimization technique in Minimax game playing prunes non-optimal branches without affecting the final evaluation outcome?",
                "explanation": "Alpha-Beta Pruning skips evaluating subtrees that cannot influence the final minimax decision.",
                "difficulty": "MEDIUM",
                "marks": 5,
                "options": [
                    ("Beam Search Pruning", False),
                    ("Alpha-Beta Pruning", True),
                    ("Simulated Annealing", False),
                    ("Gradient Pruning", False)
                ]
            }
        ]

        for idx, q_info in enumerate(sess1_mcqs):
            q_rule = ExamQuestionRule(
                question_paper_id=paper_sessions.id,
                section_rule_id=sec_sess1.id,
                question_index=idx,
                question_type="MCQ",
                marks=q_info["marks"],
                is_required=True,
                question_text=q_info["text"],
                explanation=q_info["explanation"],
                difficulty=q_info["difficulty"]
            )
            db.add(q_rule)
            await db.flush()
            for opt_text, is_corr in q_info["options"]:
                db.add(QuestionOption(
                    question_rule_id=q_rule.id,
                    option_text=opt_text,
                    is_correct=is_corr
                ))

        # Session 2: Machine Learning Principles (5 mins)
        sec_sess2 = ExamSectionRule(
            question_paper_id=paper_sessions.id,
            section_index=1,
            section_name="Session 2 - Machine Learning Principles",
            section_type="MCQ",
            section_duration_minutes=5,
            navigation_policy="SEQUENTIAL",
            allow_return_to_previous=False,
            lock_after_timeout=True,
            randomize_questions=False,
            require_completion_before_next=True,
            section_weight=1.0,
            instructions="Session 2: Time limit is strictly 5 minutes. You cannot return to Session 1."
        )
        db.add(sec_sess2)
        await db.flush()

        sess2_mcqs = [
            {
                "text": "Which learning paradigm is used when training an algorithm on unlabelled data to discover underlying inherent patterns or cluster groupings?",
                "explanation": "Unsupervised Learning processes unlabelled inputs to find clusters or dimensionality reductions.",
                "difficulty": "EASY",
                "marks": 5,
                "options": [
                    ("Supervised Classification", False),
                    ("Unsupervised Learning / Clustering", True),
                    ("Reinforcement Learning", False),
                    ("Self-Supervised Regression", False)
                ]
            },
            {
                "text": "When evaluating a binary classifier on an imbalanced dataset (e.g. 99% negative, 1% positive), which evaluation metric is most reliable?",
                "explanation": "F1-Score (harmonic mean of Precision and Recall) or Precision-Recall AUC is far more informative than raw accuracy for imbalanced classes.",
                "difficulty": "MEDIUM",
                "marks": 5,
                "options": [
                    ("Raw Accuracy", False),
                    ("F1-Score / PR-AUC", True),
                    ("Mean Squared Error", False),
                    ("R-Squared Score", False)
                ]
            },
            {
                "text": "What undesirable phenomenon occurs when a machine learning model achieves near-zero loss on training data but generalizes poorly to unseen validation data?",
                "explanation": "Overfitting happens when a model learns training noise and specific details rather than generalizable underlying trends.",
                "difficulty": "EASY",
                "marks": 5,
                "options": [
                    ("Underfitting", False),
                    ("High Bias", False),
                    ("Overfitting", True),
                    ("Vanishing Gradient", False)
                ]
            }
        ]

        for idx, q_info in enumerate(sess2_mcqs):
            q_rule = ExamQuestionRule(
                question_paper_id=paper_sessions.id,
                section_rule_id=sec_sess2.id,
                question_index=idx,
                question_type="MCQ",
                marks=q_info["marks"],
                is_required=True,
                question_text=q_info["text"],
                explanation=q_info["explanation"],
                difficulty=q_info["difficulty"]
            )
            db.add(q_rule)
            await db.flush()
            for opt_text, is_corr in q_info["options"]:
                db.add(QuestionOption(
                    question_rule_id=q_rule.id,
                    option_text=opt_text,
                    is_correct=is_corr
                ))

        # Session 3: Deep Learning & Neural Architectures (5 mins)
        sec_sess3 = ExamSectionRule(
            question_paper_id=paper_sessions.id,
            section_index=2,
            section_name="Session 3 - Deep Learning & Neural Architectures",
            section_type="MCQ",
            section_duration_minutes=5,
            navigation_policy="SEQUENTIAL",
            allow_return_to_previous=False,
            lock_after_timeout=True,
            randomize_questions=False,
            require_completion_before_next=True,
            section_weight=1.0,
            instructions="Session 3: Final 5-minute timed session."
        )
        db.add(sec_sess3)
        await db.flush()

        sess3_mcqs = [
            {
                "text": "Which mathematical activation function maps arbitrary real-valued numbers to the (0, 1) range, making it suitable for binary classification probability?",
                "explanation": "The Sigmoid function 1 / (1 + e^(-z)) maps any real input to a output between 0 and 1.",
                "difficulty": "EASY",
                "marks": 5,
                "options": [
                    ("ReLU", False),
                    ("Sigmoid", True),
                    ("Leaky ReLU", False),
                    ("Identity", False)
                ]
            },
            {
                "text": "In Convolutional Neural Networks (CNNs), what is the primary role of a Max Pooling layer?",
                "explanation": "Pooling layers downsample spatial dimensions (height and width), reducing computation and providing translation invariance.",
                "difficulty": "MEDIUM",
                "marks": 5,
                "options": [
                    ("To increase the channel depth dimension", False),
                    ("To downsample spatial dimensions and reduce computation", True),
                    ("To apply non-linear backpropagation weights", False),
                    ("To convert feature maps into one-hot labels", False)
                ]
            },
            {
                "text": "Which core mechanism enables Transformer models (such as BERT, GPT, and LLaMA) to relate tokens across arbitrary sequence distances effectively?",
                "explanation": "Scaled Dot-Product Self-Attention dynamically weighs relationships between all tokens simultaneously.",
                "difficulty": "MEDIUM",
                "marks": 5,
                "options": [
                    ("Recurrent Feedback Loops", False),
                    ("Multi-Head Self-Attention", True),
                    ("Markov Decision Chains", False),
                    ("Static Convolutional Kernels", False)
                ]
            }
        ]

        for idx, q_info in enumerate(sess3_mcqs):
            q_rule = ExamQuestionRule(
                question_paper_id=paper_sessions.id,
                section_rule_id=sec_sess3.id,
                question_index=idx,
                question_type="MCQ",
                marks=q_info["marks"],
                is_required=True,
                question_text=q_info["text"],
                explanation=q_info["explanation"],
                difficulty=q_info["difficulty"]
            )
            db.add(q_rule)
            await db.flush()
            for opt_text, is_corr in q_info["options"]:
                db.add(QuestionOption(
                    question_rule_id=q_rule.id,
                    option_text=opt_text,
                    is_correct=is_corr
                ))

        created_papers_info.append(("Session by Session (3 Sessions)", paper_sessions, 15, 45))

        # Commit all QuestionPapers and their rules
        await db.commit()

        # =========================================================================
        # 5. CREATE AND PUBLISH CORRESPONDING EXAMS FOR EACH PAPER
        # =========================================================================
        now = datetime.now(timezone.utc)
        exam_records = []

        for label, paper, total_dur, total_marks in created_papers_info:
            await db.refresh(paper)
            
            # Load full paper structure
            paper_full_query = select(QuestionPaper).options(
                selectinload(QuestionPaper.section_rules).selectinload(ExamSectionRule.question_rules).selectinload(ExamQuestionRule.options)
            ).where(QuestionPaper.id == paper.id)
            p_res = await db.execute(paper_full_query)
            loaded_paper = p_res.scalar_one()

            # Schedule start 10 minutes from now, end duration + 30 mins
            start_time = now + timedelta(minutes=10)
            end_time = start_time + timedelta(minutes=total_dur + 30)

            exam = Exam(
                uuid=str(uuid.uuid4()),
                exam_code=f"EXAM-{str(uuid.uuid4())[:8].upper()}",
                title=loaded_paper.title,
                description=loaded_paper.description,
                question_paper_id=loaded_paper.id,
                question_paper_version=loaded_paper.version,
                scheduled_start=start_time,
                scheduled_end=end_time,
                duration_minutes=total_dur,
                timezone="UTC",
                course_name=loaded_paper.course_name,
                subject=loaded_paper.course_name,
                semester=1,
                session_name="Fall 2026",
                passing_marks=int(total_marks * 0.5),
                total_marks=total_marks,
                negative_marking=False,
                auto_submit=True,
                grace_period=5,
                late_join=10,
                randomization=False,
                allow_resume_after_disconnect=True,
                global_navigation="SEQUENTIAL" if "3 Sessions" in loaded_paper.title else "FREE",
                randomize_sections=False,
                randomize_questions=False,
                allow_review_before_submit=True,
                show_remaining_time=True,
                show_question_numbers=True,
                show_marks=True,
                created_by=examiner.id,
                status="READY"
            )
            db.add(exam)
            await db.flush()

            # Clone section rules and question rules for runtime exam
            for src_sec in loaded_paper.section_rules:
                new_sec = ExamSectionRule(
                    exam_id=exam.id,
                    question_paper_id=None,
                    section_index=src_sec.section_index,
                    section_name=src_sec.section_name,
                    section_type=src_sec.section_type,
                    section_duration_minutes=src_sec.section_duration_minutes,
                    navigation_policy=src_sec.navigation_policy,
                    allow_return_to_previous=src_sec.allow_return_to_previous,
                    lock_after_timeout=src_sec.lock_after_timeout,
                    randomize_questions=src_sec.randomize_questions,
                    require_completion_before_next=src_sec.require_completion_before_next,
                    section_weight=src_sec.section_weight,
                    instructions=src_sec.instructions
                )
                db.add(new_sec)
                await db.flush()

                for src_q in src_sec.question_rules:
                    new_q = ExamQuestionRule(
                        exam_id=exam.id,
                        question_paper_id=None,
                        section_rule_id=new_sec.id,
                        question_index=src_q.question_index,
                        question_type=src_q.question_type,
                        marks=src_q.marks,
                        is_required=src_q.is_required,
                        question_text=src_q.question_text,
                        image_url=src_q.image_url,
                        explanation=src_q.explanation,
                        difficulty=src_q.difficulty,
                        character_limit=src_q.character_limit,
                        word_limit=src_q.word_limit,
                        attachment_allowed=src_q.attachment_allowed,
                        autosave=src_q.autosave,
                        individual_submission=src_q.individual_submission,
                        editable_after_submission=src_q.editable_after_submission,
                        allow_multiple_submissions=src_q.allow_multiple_submissions,
                        max_submission_count=src_q.max_submission_count,
                        allow_editing_until_final=src_q.allow_editing_until_final,
                        lock_immediately_after_submission=src_q.lock_immediately_after_submission,
                        show_correctness_immediately=src_q.show_correctness_immediately,
                        instructions=src_q.instructions
                    )
                    db.add(new_q)
                    await db.flush()

                    for src_opt in src_q.options:
                        db.add(QuestionOption(
                            question_rule_id=new_q.id,
                            option_text=src_opt.option_text,
                            is_correct=src_opt.is_correct
                        ))

            exam_records.append((label, exam))

        await db.commit()

        print("\n=======================================================")
        print("  SUCCESSFULLY CREATED 4 PAPERS & EXAMS FOR EXAMINER   ")
        print("=======================================================")
        for (label, p, dur, marks), (_, exam) in zip(created_papers_info, exam_records):
            print(f"\n[{label.upper()}]")
            print(f"  • Paper ID       : {p.id}")
            print(f"  • Title          : {p.title}")
            print(f"  • Course         : {p.course_name}")
            print(f"  • Status         : {p.status}")
            print(f"  • Mode           : {p.mode}")
            print(f"  • Exam ID        : {exam.id}")
            print(f"  • Exam Code      : {exam.exam_code}")
            print(f"  • Total Duration : {exam.duration_minutes} minutes")
            print(f"  • Total Marks    : {exam.total_marks}")

if __name__ == "__main__":
    asyncio.run(create_papers_for_examiner())
