import puppeteer from 'puppeteer';

(async () => {
  const browser = await puppeteer.launch({
    headless: 'new',
    executablePath: 'C:\\Users\\PMLS\\.cache\\puppeteer\\chrome\\win64-150.0.7871.24\\chrome-win64\\chrome.exe'
  });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('BROWSER CONSOLE:', msg.text()));
  page.on('pageerror', error => console.log('BROWSER ERROR:', error.message));
  page.on('response', response => {
    // console.log(`RESPONSE: ${response.status()} ${response.url()}`);
  });
  
  console.log('Navigating to http://localhost:5174/');
  await page.goto('http://localhost:5174/');
  
  console.log('Waiting for Student card');
  await page.waitForSelector('text/Student');
  
  console.log('Clicking Student card');
  const [studentCard] = await page.$$('text/Student');
  if (studentCard) {
    await studentCard.click();
    console.log('Clicked!');
  } else {
    console.log('Student card not found');
  }
  
  await new Promise(r => setTimeout(r, 2000));
  console.log('Current URL:', page.url());
  
  await browser.close();
})();
