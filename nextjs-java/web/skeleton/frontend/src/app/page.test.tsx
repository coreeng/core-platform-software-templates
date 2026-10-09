import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Notes from "./page";
test("validates before posting, then saves and refreshes list", async () => {
  const fetcher = jest.fn().mockResolvedValueOnce({ ok: true, json: async () => [] })
    .mockResolvedValueOnce({ ok: true })
    .mockResolvedValueOnce({ ok: true, json: async () => [{ id: "1", text: "Saved note" }] });
  global.fetch = fetcher;
  render(<Notes />);
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByText("Save note"));
  expect(await screen.findByRole("alert")).toHaveTextContent("1–200");
  expect(fetcher).toHaveBeenCalledTimes(1);
  fireEvent.change(screen.getByLabelText(/Note \(/), { target: { value: "Saved note" } });
  fireEvent.click(screen.getByText("Save note"));
  expect(await screen.findByText("Saved note")).toBeInTheDocument();
  expect(fetcher).toHaveBeenNthCalledWith(2, "/api/notes", expect.objectContaining({ method: "POST", body: '{"text":"Saved note"}' }));
});
