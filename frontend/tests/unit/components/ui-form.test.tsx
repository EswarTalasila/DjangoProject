import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useForm, FormProvider } from "react-hook-form";

import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormDescription,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";

/* ------------------------------------------------------------------ */
/*  Helper wrapper that provides react-hook-form context               */
/* ------------------------------------------------------------------ */
function TestForm({
  defaultValues,
  children,
}: {
  defaultValues?: Record<string, string>;
  children: React.ReactNode;
}) {
  const form = useForm({ defaultValues: defaultValues ?? { name: "" } });
  return <Form {...form}>{children}</Form>;
}

/* ------------------------------------------------------------------ */
/*  FormItem                                                           */
/* ------------------------------------------------------------------ */
describe("FormItem", () => {
  it("renders children with data-slot", () => {
    render(
      <TestForm>
        <FormField
          name="name"
          render={() => (
            <FormItem>
              <span>Inside item</span>
            </FormItem>
          )}
        />
      </TestForm>,
    );
    expect(screen.getByText("Inside item")).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <TestForm>
        <FormField
          name="name"
          render={() => (
            <FormItem className="custom-class">
              <span>child</span>
            </FormItem>
          )}
        />
      </TestForm>,
    );
    const item = container.querySelector('[data-slot="form-item"]');
    expect(item).toHaveClass("custom-class");
  });
});

/* ------------------------------------------------------------------ */
/*  FormLabel                                                          */
/* ------------------------------------------------------------------ */
describe("FormLabel", () => {
  it("renders with data-slot", () => {
    const { container } = render(
      <TestForm>
        <FormField
          name="name"
          render={() => (
            <FormItem>
              <FormLabel>Username</FormLabel>
            </FormItem>
          )}
        />
      </TestForm>,
    );
    const label = container.querySelector('[data-slot="form-label"]');
    expect(label).toBeInTheDocument();
    expect(label).toHaveTextContent("Username");
  });
});

/* ------------------------------------------------------------------ */
/*  FormControl                                                        */
/* ------------------------------------------------------------------ */
describe("FormControl", () => {
  it("renders child input with proper aria attributes", () => {
    render(
      <TestForm>
        <FormField
          name="name"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Name</FormLabel>
              <FormControl>
                <Input placeholder="Enter name" {...field} />
              </FormControl>
            </FormItem>
          )}
        />
      </TestForm>,
    );
    const input = screen.getByPlaceholderText("Enter name");
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute("aria-invalid", "false");
  });
});

/* ------------------------------------------------------------------ */
/*  FormDescription                                                    */
/* ------------------------------------------------------------------ */
describe("FormDescription", () => {
  it("renders description text", () => {
    const { container } = render(
      <TestForm>
        <FormField
          name="name"
          render={() => (
            <FormItem>
              <FormDescription>Enter your display name.</FormDescription>
            </FormItem>
          )}
        />
      </TestForm>,
    );
    const desc = container.querySelector('[data-slot="form-description"]');
    expect(desc).toHaveTextContent("Enter your display name.");
  });
});

/* ------------------------------------------------------------------ */
/*  FormMessage                                                        */
/* ------------------------------------------------------------------ */
describe("FormMessage", () => {
  it("renders children when there is no error", () => {
    const { container } = render(
      <TestForm>
        <FormField
          name="name"
          render={() => (
            <FormItem>
              <FormMessage>Custom message</FormMessage>
            </FormItem>
          )}
        />
      </TestForm>,
    );
    const msg = container.querySelector('[data-slot="form-message"]');
    expect(msg).toHaveTextContent("Custom message");
  });

  it("returns null when there is no error and no children", () => {
    const { container } = render(
      <TestForm>
        <FormField
          name="name"
          render={() => (
            <FormItem>
              <FormMessage />
            </FormItem>
          )}
        />
      </TestForm>,
    );
    const msg = container.querySelector('[data-slot="form-message"]');
    expect(msg).toBeNull();
  });
});
