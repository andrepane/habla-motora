import {chromium as engine} from 'playwright';
// Optional executable for environments without Playwright's managed download.
export const chromium={...engine,launch:options=>engine.launch({...options,
  ...(process.env.BROWSER_EXECUTABLE?{executablePath:process.env.BROWSER_EXECUTABLE,args:[...(options?.args??[]),'--no-sandbox','--disable-gpu']}:{}),
})};
