package com.example.heal;

import com.epam.healenium.SelfHealingDriver;
import org.openqa.selenium.*;
import org.openqa.selenium.chrome.ChromeDriver;
import java.io.*;
import java.time.LocalDateTime;

public class HealDemo {
    public static void main(String[] args) throws Exception {
        String phase = (args != null && args.length > 0) ? args[0] : "learn";
        System.out.println("[INFO] Phase: " + phase);

        WebDriver raw = new ChromeDriver();
        WebDriver driver = SelfHealingDriver.create(raw);

        String url = "https://example.org/";
        driver.get(url);

        File logDir = new File("runs"); logDir.mkdirs();
        String logName = "runs/healenium_run_" + phase + "_" + System.currentTimeMillis() + ".log";
        try (PrintWriter out = new PrintWriter(new FileWriter(logName, true))) {
            out.println("ts=" + LocalDateTime.now() + " phase=" + phase);

            try {
                if ("learn".equalsIgnoreCase(phase)) {
                    WebElement el = driver.findElement(By.cssSelector("h1"));
                    String text = el.getText();
                    out.println("learn.success=true text=" + text);
                    System.out.println("[LEARN] Found h1: " + text);
                } else {
                    WebElement el = driver.findElement(By.cssSelector("h1.title")); // wrong on purpose
                    String text = el.getText();
                    out.println("heal.success=true text=" + text);
                    System.out.println("[HEAL] Found element (healed): " + text);
                }
            } catch (NoSuchElementException nse) {
                out.println("heal.success=false error=NoSuchElementException");
                System.out.println("[HEAL] Healing failed: " + nse.getMessage());
            } catch (Exception ex) {
                out.println("heal.success=false error=" + ex.getClass().getSimpleName());
                System.out.println("[ERROR] " + ex.getMessage());
            }
        } finally {
            driver.quit();
        }
        System.out.println("[INFO] Log written. Check runs/ folder.");
    }
}
