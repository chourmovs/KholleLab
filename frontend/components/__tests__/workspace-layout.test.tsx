import {render,screen} from "@testing-library/react";
import {expect,it} from "vitest";
import {WorkspaceLayout} from "../workspace-layout";

it("applies the collapsed workspace class from statement state",()=>{const{rerender}=render(<WorkspaceLayout statement="statement" blackboard="board" tools="tools" professor="professor"/>);expect(screen.getByTestId("workspace")).not.toHaveClass("statement-collapsed");rerender(<WorkspaceLayout statement="statement" blackboard="board" tools="tools" professor="professor" statementExpanded={false}/>);expect(screen.getByTestId("workspace")).toHaveClass("statement-collapsed")});
