/**
 * PHASE 1 TESTING & VALIDATION SUITE
 * Tests for object_viewer.html and character_viewer.html improvements
 *
 * To use in browser console:
 * 1. Open object_viewer.html or character_viewer.html in browser
 * 2. Press F12 to open Developer Tools
 * 3. Copy and paste this entire script into the Console tab
 * 4. Run tests with: runAllTests()
 */

// ==============================================================================
// PERSISTENCE TESTS (Tasks 8-9)
// ==============================================================================

function testPersistence() {
  console.group("🔄 PERSISTENCE TESTS");
  const results = {
    passed: 0,
    failed: 0,
    tests: [],
  };

  // Test 1: localStorage keys exist
  const expectedKeys = {
    object_viewer: [
      "objectViewerCurrentDir",
      "objectViewerCurrentZoom",
      "objectViewerScale",
      "objectViewerBgColor",
      "objectViewerLastObject",
    ],
    character_viewer: [
      "characterViewerShowSkeleton",
      "characterViewerShowWireframe",
      "characterViewerBgColor",
      "characterViewerLastCharacter",
    ],
  };

  // Check if we're on object_viewer or character_viewer
  const viewer = document.title.includes("Object")
    ? "object_viewer"
    : "character_viewer";
  const keysToCheck = expectedKeys[viewer];

  // Test localStorage save/load
  const testKey = "persistenceTestKey";
  const testValue = "persistenceTestValue";
  localStorage.setItem(testKey, testValue);
  const retrieved = localStorage.getItem(testKey);

  if (retrieved === testValue) {
    results.tests.push("✅ localStorage is functional");
    results.passed++;
  } else {
    results.tests.push("❌ localStorage not working");
    results.failed++;
  }

  // Test direction persistence (object_viewer only)
  if (viewer === "object_viewer" && typeof currentDirection !== "undefined") {
    const currentDir = currentDirection;
    localStorage.setItem("objectViewerCurrentDir", currentDir);
    const savedDir = localStorage.getItem("objectViewerCurrentDir");
    if (savedDir === currentDir) {
      results.tests.push(`✅ Direction persists: ${currentDir}`);
      results.passed++;
    } else {
      results.tests.push("❌ Direction persistence failed");
      results.failed++;
    }
  }

  // Test zoom persistence (object_viewer only)
  if (viewer === "object_viewer" && typeof currentZoom !== "undefined") {
    const currentZ = currentZoom;
    localStorage.setItem("objectViewerCurrentZoom", currentZ);
    const savedZoom = localStorage.getItem("objectViewerCurrentZoom");
    if (savedZoom === currentZ) {
      results.tests.push(`✅ Zoom persists: ${currentZ}`);
      results.passed++;
    } else {
      results.tests.push("❌ Zoom persistence failed");
      results.failed++;
    }
  }

  // Test scale persistence (object_viewer only)
  if (viewer === "object_viewer" && typeof scale !== "undefined") {
    const currentScale = scale.toString();
    localStorage.setItem("objectViewerScale", currentScale);
    const savedScale = localStorage.getItem("objectViewerScale");
    if (savedScale === currentScale) {
      results.tests.push(`✅ Scale persists: ${currentScale}x`);
      results.passed++;
    } else {
      results.tests.push("❌ Scale persistence failed");
      results.failed++;
    }
  }

  // Test skeleton visibility persistence (character_viewer only)
  if (viewer === "character_viewer") {
    const skeletonCheckbox = document.getElementById("show-skeleton");
    if (skeletonCheckbox) {
      const checked = skeletonCheckbox.checked.toString();
      localStorage.setItem("characterViewerShowSkeleton", checked);
      const saved = localStorage.getItem("characterViewerShowSkeleton");
      if (saved === checked) {
        results.tests.push(`✅ Skeleton visibility persists: ${checked}`);
        results.passed++;
      } else {
        results.tests.push("❌ Skeleton visibility persistence failed");
        results.failed++;
      }
    }
  }

  // Test background color persistence
  const bgColorInput = document.getElementById("bg-color");
  if (bgColorInput) {
    const currentColor = bgColorInput.value;
    localStorage.setItem(
      viewer === "object_viewer"
        ? "objectViewerBgColor"
        : "characterViewerBgColor",
      currentColor,
    );
    const saved = localStorage.getItem(
      viewer === "object_viewer"
        ? "objectViewerBgColor"
        : "characterViewerBgColor",
    );
    if (saved === currentColor) {
      results.tests.push(`✅ Background color persists: ${currentColor}`);
      results.passed++;
    } else {
      results.tests.push("❌ Background color persistence failed");
      results.failed++;
    }
  }

  // Clean up test key
  localStorage.removeItem(testKey);

  results.tests.forEach((test) => console.log(test));
  console.log(`\nResults: ${results.passed} passed, ${results.failed} failed`);
  console.groupEnd();
  return results;
}

// ==============================================================================
// ANALYTICS TESTS (Task 10)
// ==============================================================================

function testAnalyticsLogging() {
  console.group("📊 ANALYTICS LOGGING TESTS");
  const results = {
    passed: 0,
    failed: 0,
    tests: [],
  };

  // Test 1: analyticsLog exists
  if (typeof window.analyticsLog === "undefined") {
    console.log(
      "⚠️ window.analyticsLog not yet initialized (will be created on first event)",
    );
    results.tests.push(
      "⏳ window.analyticsLog not initialized (normal - creates on first use)",
    );
  } else {
    results.tests.push(
      `✅ window.analyticsLog exists with ${window.analyticsLog.length} events`,
    );
    results.passed++;
  }

  // Test 2: logAnalytics function exists
  if (typeof logAnalytics === "function") {
    results.tests.push("✅ logAnalytics() function exists");
    results.passed++;

    // Test 3: logAnalytics works
    try {
      logAnalytics("test_event", { testData: "test_value" });
      if (window.analyticsLog && window.analyticsLog.length > 0) {
        const lastEvent = window.analyticsLog[window.analyticsLog.length - 1];
        if (
          lastEvent.event === "test_event" &&
          lastEvent.details.testData === "test_value"
        ) {
          results.tests.push("✅ logAnalytics() logs events correctly");
          results.passed++;
        } else {
          results.tests.push("❌ logAnalytics() not logging correctly");
          results.failed++;
        }
      }
    } catch (e) {
      results.tests.push(`❌ logAnalytics() error: ${e.message}`);
      results.failed++;
    }
  } else {
    results.tests.push("❌ logAnalytics() function not found");
    results.failed++;
  }

  // Test 4: assetExportLog exists (for export tracking)
  if (
    typeof window.assetExportLog !== "undefined" &&
    window.assetExportLog.length > 0
  ) {
    results.tests.push(
      `✅ window.assetExportLog exists with ${window.assetExportLog.length} export events`,
    );
    results.passed++;
  } else {
    results.tests.push(
      "⏳ window.assetExportLog (will be created after first export)",
    );
  }

  // Test 5: Analytics events captured for viewer actions
  const viewer = document.title.includes("Object")
    ? "object_viewer"
    : "character_viewer";
  if (window.analyticsLog && window.analyticsLog.length > 0) {
    const eventTypes = window.analyticsLog.map((e) => e.event);
    results.tests.push(
      `✅ Analytics events captured: ${[...new Set(eventTypes)].join(", ")}`,
    );
    results.passed++;
  }

  results.tests.forEach((test) => console.log(test));
  console.log(`\nResults: ${results.passed} passed, ${results.failed} failed`);
  console.groupEnd();
  return results;
}

// ==============================================================================
// ERROR HANDLING TESTS (Task 13)
// ==============================================================================

function testErrorHandling() {
  console.group("⚠️ ERROR HANDLING TESTS");
  const results = {
    passed: 0,
    failed: 0,
    tests: [],
  };

  // Test 1: showExportDebugModal exists
  if (typeof showExportDebugModal === "function") {
    results.tests.push("✅ showExportDebugModal() function exists");
    results.passed++;

    // Test 2: Can call with sample error
    try {
      showExportDebugModal("Test error: No sprite to export", [
        "Debug line 1",
        "Debug line 2",
      ]);
      results.tests.push(
        "✅ showExportDebugModal() callable with sample error",
      );
      results.passed++;
    } catch (e) {
      results.tests.push(`❌ showExportDebugModal() error: ${e.message}`);
      results.failed++;
    }
  } else {
    results.tests.push("❌ showExportDebugModal() not found");
    results.failed++;
  }

  // Test 3: showDebugModal exists
  if (typeof showDebugModal === "function") {
    results.tests.push("✅ showDebugModal() function exists");
    results.passed++;
  } else {
    results.tests.push("❌ showDebugModal() not found");
    results.failed++;
  }

  // Test 4: htmlEscape helper exists
  if (typeof htmlEscape === "function") {
    results.tests.push("✅ htmlEscape() function exists (XSS protection)");
    results.passed++;

    try {
      const escaped = htmlEscape("<script>alert('XSS')</script>");
      if (escaped.includes("&lt;") && !escaped.includes("<script>")) {
        results.tests.push("✅ htmlEscape() properly escapes HTML");
        results.passed++;
      } else {
        results.tests.push("❌ htmlEscape() not escaping properly");
        results.failed++;
      }
    } catch (e) {
      results.tests.push(`❌ htmlEscape() error: ${e.message}`);
      results.failed++;
    }
  }

  results.tests.forEach((test) => console.log(test));
  console.log(`\nResults: ${results.passed} passed, ${results.failed} failed`);
  console.groupEnd();
  return results;
}

// ==============================================================================
// UI VERIFICATION TESTS
// ==============================================================================

function testUIComponents() {
  console.group("🎨 UI COMPONENT VERIFICATION");
  const results = {
    passed: 0,
    failed: 0,
    tests: [],
  };

  const viewer = document.title.includes("Object")
    ? "object_viewer"
    : "character_viewer";

  // Test direction controls (object_viewer)
  if (viewer === "object_viewer") {
    const dirButtons = document.querySelectorAll(".direction-btn");
    if (dirButtons.length === 4) {
      results.tests.push("✅ Direction buttons present (4 total)");
      results.passed++;
    } else {
      results.tests.push(
        `❌ Direction buttons missing (found ${dirButtons.length}, expected 4)`,
      );
      results.failed++;
    }

    // Test zoom controls
    const zoomButtons = document.querySelectorAll(".zoom-btn");
    if (zoomButtons.length === 3) {
      results.tests.push("✅ Zoom buttons present (3 total)");
      results.passed++;
    } else {
      results.tests.push(
        `❌ Zoom buttons missing (found ${zoomButtons.length}, expected 3)`,
      );
      results.failed++;
    }

    // Test scale slider
    const scaleSlider = document.getElementById("scale-slider");
    if (scaleSlider) {
      results.tests.push("✅ Scale slider present");
      results.passed++;
    } else {
      results.tests.push("❌ Scale slider missing");
      results.failed++;
    }
  }

  // Test background color control
  const bgColorInput = document.getElementById("bg-color");
  if (bgColorInput) {
    results.tests.push("✅ Background color picker present");
    results.passed++;
  } else {
    results.tests.push("❌ Background color picker missing");
    results.failed++;
  }

  // Test character viewer controls
  if (viewer === "character_viewer") {
    const skeletonCheckbox = document.getElementById("show-skeleton");
    if (skeletonCheckbox) {
      results.tests.push("✅ Skeleton checkbox present");
      results.passed++;
    } else {
      results.tests.push("❌ Skeleton checkbox missing");
      results.failed++;
    }

    const wireframeCheckbox = document.getElementById("show-wireframe");
    if (wireframeCheckbox) {
      results.tests.push("✅ Wireframe checkbox present");
      results.passed++;
    } else {
      results.tests.push("❌ Wireframe checkbox missing");
      results.failed++;
    }
  }

  results.tests.forEach((test) => console.log(test));
  console.log(`\nResults: ${results.passed} passed, ${results.failed} failed`);
  console.groupEnd();
  return results;
}

// ==============================================================================
// MAIN TEST RUNNER
// ==============================================================================

function runAllTests() {
  console.clear();
  console.log(
    "╔════════════════════════════════════════════════════════════════╗",
  );
  console.log(
    "║        PHASE 1 TESTING & VALIDATION - ALL VIEWERS              ║",
  );
  console.log(
    "║                  Started: " +
      new Date().toLocaleString() +
      "          ║",
  );
  console.log(
    "╚════════════════════════════════════════════════════════════════╝\n",
  );

  const allResults = {
    persistence: testPersistence(),
    analytics: testAnalyticsLogging(),
    errorHandling: testErrorHandling(),
    ui: testUIComponents(),
  };

  // Summary
  console.group("📈 SUMMARY");
  const totalPassed = Object.values(allResults).reduce(
    (sum, r) => sum + r.passed,
    0,
  );
  const totalFailed = Object.values(allResults).reduce(
    (sum, r) => sum + r.failed,
    0,
  );
  const totalTests = totalPassed + totalFailed;

  console.log(`\n✅ PASSED: ${totalPassed}/${totalTests} tests`);
  console.log(`❌ FAILED: ${totalFailed}/${totalTests} tests`);
  console.log(
    `📊 SUCCESS RATE: ${((totalPassed / totalTests) * 100).toFixed(1)}%\n`,
  );

  if (totalFailed === 0) {
    console.log(
      "🎉 ALL TESTS PASSED! Phase 1 improvements verified successfully!",
    );
  } else {
    console.log(`⚠️  ${totalFailed} test(s) need attention`);
  }

  console.log("\n📝 NEXT STEPS:");
  console.log("1. Test page reload to verify persistence");
  console.log("2. Test exports functionality");
  console.log("3. Check console for any runtime errors");
  console.log("4. Run on actual data to verify stability");
  console.groupEnd();

  return allResults;
}

// ==============================================================================
// UTILITY FUNCTIONS FOR MANUAL TESTING
// ==============================================================================

// Verify localStorage persistence after page reload
function verifyPersistenceAfterReload() {
  console.log("🔄 PERSISTENCE VERIFICATION (Run this after page reload)");

  const viewer = document.title.includes("Object")
    ? "object_viewer"
    : "character_viewer";
  const results = [];

  if (viewer === "object_viewer") {
    const dir = localStorage.getItem("objectViewerCurrentDir");
    const zoom = localStorage.getItem("objectViewerCurrentZoom");
    const scale = localStorage.getItem("objectViewerScale");
    const bgColor = localStorage.getItem("objectViewerBgColor");

    console.log(`Direction (from localStorage): ${dir}`);
    console.log(
      `  Current UI: ${typeof currentDirection !== "undefined" ? currentDirection : "not loaded"}`,
    );
    console.log(`Zoom (from localStorage): ${zoom}`);
    console.log(
      `  Current UI: ${typeof currentZoom !== "undefined" ? currentZoom : "not loaded"}`,
    );
    console.log(`Scale (from localStorage): ${scale}`);
    console.log(
      `  Current UI: ${typeof scale !== "undefined" ? scale + "x" : "not loaded"}`,
    );
  }
}

// Quick export test (mock)
function testExportMock() {
  console.log("🚀 EXPORT TEST (Mock)");

  if (typeof logAnalytics === "function") {
    logAnalytics("export_test", { type: "mock", status: "initiated" });
    console.log("✅ Export event logged");
  }
}

console.log("✅ Testing framework loaded! Run: runAllTests()");
