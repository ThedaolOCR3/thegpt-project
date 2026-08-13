export interface User {
  id: string;
  email: string;
  profile_image_url: string | null;
  is_email_verified: boolean;
  is_admin: boolean;
  created_at: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: 'bearer';
  user: User;
}
