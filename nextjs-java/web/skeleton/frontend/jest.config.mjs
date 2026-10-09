import nextJest from "next/jest.js";
export default nextJest({ dir: "./" })({ testEnvironment: "jsdom", setupFilesAfterEnv: ["@testing-library/jest-dom"] });
