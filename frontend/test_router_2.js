import { createMemoryRouter } from 'react-router-dom';

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
  },
  { path: '*', id: '404' }
];

const router = createMemoryRouter(routes, {
  initialEntries: ['/student/login']
});

console.log('Matches for /student/login:', router.state.matches.map(m => m.route.id));

const router2 = createMemoryRouter(routes, {
  initialEntries: ['/student']
});
console.log('Matches for /student:', router2.state.matches.map(m => m.route.id));
