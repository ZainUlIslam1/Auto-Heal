import com.epam.healenium.SelfHealingDriver;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.remote.RemoteWebDriver;
import org.junit.jupiter.api.*;

import java.net.URI;

public class HealeniumSmokeTest {
    private WebDriver raw;
    private WebDriver driver;

    @BeforeEach
    void setUp() throws Exception {
        ChromeOptions options = new ChromeOptions();
        // local Chrome; comment out if you use Remote Grid
        raw = new org.openqa.selenium.chrome.ChromeDriver(options);

        // Wrap with Healenium
        driver = SelfHealingDriver.create(raw);
    }

    @AfterEach
    void tearDown() {
        if (driver != null) driver.quit();
    }

    @Test
    void healsChangedLocator() {
        driver.get("https://the-internet.herokuapp.com/login");
        // Intentionally brittle id (simulate later change)
        driver.findElement(By.id("username")).sendKeys("tomsmith");
        driver.findElement(By.id("password")).sendKeys("SuperSecretPassword!");
        driver.findElement(By.cssSelector("button[type='submit']")).click();
        Assertions.assertTrue(driver.getPageSource().contains("You logged into a secure area!"));
    }
}
