-- Part 8: programming language of a question's code snippet (for syntax highlighting and verification).
alter table questions
  add column language text not null default 'python' check (language in ('python', 'cpp'));
