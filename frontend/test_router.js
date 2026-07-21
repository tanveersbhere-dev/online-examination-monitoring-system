import { createMemoryRouter, matchRoutes } from 'react-router-dom';

const routes = [
  {
    path: '/student',
    id: 'open-student',
    children: [
      { path: 'login', id: 'student-login' },
    ],
  },
  {
    path: '/student',
    id: 'protected-student',
    children: [
      {
        id: 'protected-wrapper',
        children: [
          { index: true, id: 'student-index' },
          { path: 'instructions', id: 'student-instructions' }
        ]
      }
    ]
  }
];

console.log('Match for /student:', matchRoutes(routes, '/student'));
console.log('Match for /student/login:', matchRoutes(routes, '/student/login'));
