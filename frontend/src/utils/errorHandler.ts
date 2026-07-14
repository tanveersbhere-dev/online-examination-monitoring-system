import axios from 'axios';

export const getErrorMessage = (error: any): string => {
  if (axios.isAxiosError(error)) {
    if (!error.response) {
      if (error.code === 'ECONNABORTED') {
        return 'The server is taking too long to respond.';
      }
      return 'Cannot connect to server. Please check your connection.';
    }

    const status = error.response.status;
    const data = error.response.data;

    if (status === 204) {
      return ''; // No Content, handled silently usually but good to have
    }

    if (status === 400) {
      return data?.detail || data?.message || 'Bad request. Please check your input.';
    }

    if (status === 401) {
      return data?.detail || data?.message || 'Invalid email or password.';
    }

    if (status === 403) {
      return data?.detail || data?.message || 'You do not have permission to perform this action.';
    }

    if (status === 404) {
      return data?.detail || data?.message || 'Requested resource was not found.';
    }

    if (status === 409) {
      return data?.detail || data?.message || 'Conflict error occurred.';
    }

    if (status === 422) {
      if (data?.detail && Array.isArray(data.detail) && data.detail.length > 0) {
        return data.detail[0].msg || 'Validation error.';
      }
      return data?.detail || data?.message || 'Unprocessable entity.';
    }

    if (status === 500) {
      return 'An internal server error occurred. Please try again later.';
    }

    return data?.detail || data?.message || 'An unexpected error occurred.';
  }

  if (error instanceof Error) {
    return error.message;
  }

  return 'An unexpected error occurred.';
};
