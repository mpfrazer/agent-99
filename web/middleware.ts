import { NextRequest, NextResponse } from 'next/server';

const PUBLIC_PATHS = ['/login', '/api/'];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Allow public paths and all API routes (auth handled by FastAPI)
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    return NextResponse.next();
  }

  // Check the non-httpOnly flag cookie (presence means there should be a session)
  const loggedIn = req.cookies.get('agent99_logged_in');
  if (!loggedIn) {
    const loginUrl = req.nextUrl.clone();
    loginUrl.pathname = '/login';
    loginUrl.searchParams.set('from', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
